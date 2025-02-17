from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from web3 import Web3
from decouple import config
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction
from .serializers import (
    WalletAddressSerializer,
    StatsSerializer,
    TransactionSerializer,
)  # noqa
from rest_framework.permissions import AllowAny
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q


class FaucetFundView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(csrf_exempt)
    @method_decorator(ratelimit(key="ip", rate="1/m", method=["POST"]))
    def post(self, request):
        serializer = WalletAddressSerializer(data=request.data)
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
    permission_classes = [AllowAny]

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


@api_view(["GET"])
@permission_classes([AllowAny])
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
                        "error": "Invalid from_date format. Use ISO format (e.g., 2024-02-17T16:00:00Z)"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {
                    "error": "Invalid from_date format. Use ISO format (e.g., 2024-02-17T16:00:00Z)"
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
                        "error": "Invalid to_date format. Use ISO format (e.g., 2024-02-17T16:00:00Z)"
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

    serializer = TransactionSerializer(queryset, many=True)
    return Response(serializer.data)
