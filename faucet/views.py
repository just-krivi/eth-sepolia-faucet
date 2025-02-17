from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from web3 import Web3
from decouple import config
from django_ratelimit.core import get_usage
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .schemas import (
    TransactionQueryParamsSerializer,
    WalletRequestSerializer,
    TransactionSerializer,
)
from rest_framework.permissions import BasePermission


class AllowAnyPermission(BasePermission):
    def has_permission(self, request, view):
        return True


@method_decorator(csrf_exempt, name="dispatch")
class FaucetFundView(APIView):
    permission_classes = [AllowAnyPermission]
    authentication_classes = []

    def get_ratelimit_exception_response(self, request):
        """Custom rate limit exceeded response"""
        return Response(
            {"error": "Rate limit exceeded. Please wait before requesting again."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    @extend_schema(
        request=WalletRequestSerializer,
        responses={200: dict, 400: dict, 429: dict},
        description="Request Sepolia ETH to be sent to your wallet",
    )
    def post(self, request):
        # Check rate limit
        usage = get_usage(request, group="faucet", key="ip", rate="1/m")
        if usage and usage.get("should_limit", False):
            return self.get_ratelimit_exception_response(request)

        serializer = WalletRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        wallet_address = serializer.validated_data["wallet_address"]

        # Check if the wallet has received funds in the last minute
        one_minute_ago = timezone.now() - timedelta(
            minutes=int(config("FAUCET_INTERVAL_MIN"))
        )
        if Transaction.objects.filter(
            wallet_address=wallet_address,
            created_at__gte=one_minute_ago,
            status="success",
        ).exists():
            return Response(
                {"error": "Rate limit exceeded for this wallet"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider(config("ETHEREUM_NODE_URL")))

        # Get the sender's account
        account = w3.eth.account.from_key(config("PRIVATE_KEY"))

        try:
            # Prepare transaction
            transaction = {
                "nonce": w3.eth.get_transaction_count(account.address),
                "to": wallet_address,
                "value": w3.to_wei(config("FAUCET_AMOUNT"), "ether"),
                "gas": 21000,
                "gasPrice": w3.eth.gas_price,
                "chainId": int(config("CHAIN_ID")),
            }

            # Sign and send transaction
            signed_txn = account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # Save transaction to database
            Transaction.objects.create(
                wallet_address=wallet_address,
                transaction_hash=tx_hash.hex(),
                amount=config("FAUCET_AMOUNT"),
                status="success",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {"transaction_hash": tx_hash.hex()}, status=status.HTTP_200_OK
            )

        except Exception as e:
            # Save failed transaction
            Transaction.objects.create(
                wallet_address=wallet_address,
                transaction_hash="",
                amount=config("FAUCET_AMOUNT"),
                status="failed",
                error_message=str(e),
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaucetStatsView(APIView):
    permission_classes = [AllowAnyPermission]
    authentication_classes = []

    @extend_schema(
        responses={200: dict}, description="Get statistics about faucet usage"
    )
    def get(self, request):
        # Get stats for the last 24 hours
        last_24h = timezone.now() - timedelta(hours=24)

        stats = {
            "total_transactions": Transaction.objects.count(),
            "last_24h_transactions": Transaction.objects.filter(
                created_at__gte=last_24h
            ).count(),
            "successful_transactions": Transaction.objects.filter(
                created_at__gte=last_24h, status="success"
            ).count(),
            "failed_transactions": Transaction.objects.filter(
                created_at__gte=last_24h, status="failed"
            ).count(),
        }

        return Response(stats, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="wallet",
            description="Filter by wallet address",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="from_date",
            description="Filter transactions after this date (ISO format)",
            required=False,
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="to_date",
            description="Filter transactions before this date (ISO format)",
            required=False,
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
        ),
    ],
    responses={200: list, 400: dict},
)
@api_view(["GET"])
@permission_classes([AllowAnyPermission])
def transaction_list(request):
    """
    List all transactions with optional filtering by date range and wallet address.
    """
    queryset = Transaction.objects.all()

    # Filter by wallet address
    wallet = request.query_params.get("wallet", None)
    if wallet:
        queryset = queryset.filter(wallet_address__iexact=wallet)

    # Filter by date range
    from_date = request.query_params.get("from_date", None)
    to_date = request.query_params.get("to_date", None)

    if from_date:
        try:
            from_date = parse_datetime(from_date)
            if from_date:
                queryset = queryset.filter(created_at__gte=from_date)
            else:
                return Response(
                    {
                        "error": "Invalid from_date format. Use ISO format (e.g., 2024-02-17T16:00:00Z)"  # noqa
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {
                    "error": "Invalid from_date format. Use ISO format (e.g., 2024-02-17T16:00:00Z)"  # noqa
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    if to_date:
        try:
            to_date = parse_datetime(to_date)
            if to_date:
                queryset = queryset.filter(created_at__lte=to_date)
            else:
                return Response(
                    {
                        "error": "Invalid to_date format. Use ISO format (e.g., 2024-02-17T16:00:00Z)"  # noqa
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {
                    "error": "Invalid to_date format. Use ISO format (e.g., 2024-02-17T16:00:00Z)"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Always order by created_at descending (newest first)
    queryset = queryset.order_by("-created_at")

    # Validate query parameters
    query_params_serializer = TransactionQueryParamsSerializer(
        data=request.query_params
    )
    if not query_params_serializer.is_valid():
        return Response(
            query_params_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    serializer = TransactionSerializer(queryset, many=True)
    return Response(serializer.data)
