from rest_framework import serializers
from .models import Transaction


class TransactionQueryParamsSerializer(serializers.Serializer):
    wallet = serializers.CharField(required=False, max_length=42)
    from_date = serializers.DateTimeField(required=False)
    to_date = serializers.DateTimeField(required=False)

    def validate(self, data):
        if data.get("from_date") and data.get("to_date"):
            if data["from_date"] > data["to_date"]:
                raise serializers.ValidationError("from_date must be before to_date")
        return data


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "transaction_hash",
            "amount",
            "status",
            "created_at",
            "wallet_address",
        ]
        extra_kwargs = {"transaction_hash": {"allow_blank": True}}

    def validate_transaction_hash(self, value):
        # Allow empty transaction hash for failed transactions
        if not value:
            return value

        if not value.startswith("0x"):
            raise serializers.ValidationError("Transaction hash must start with '0x'")
        try:
            int(value[2:], 16)
        except ValueError:
            raise serializers.ValidationError("Invalid hexadecimal transaction hash")
        return value

    def validate_wallet_address(self, value):
        if not value.startswith("0x"):
            raise serializers.ValidationError("Wallet address must start with '0x'")
        try:
            int(value[2:], 16)
        except ValueError:
            raise serializers.ValidationError("Invalid hexadecimal wallet address")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

    def validate_status(self, value):
        valid_statuses = ["success", "failed"]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value


class WalletRequestSerializer(serializers.Serializer):
    wallet_address = serializers.CharField(
        max_length=42,
        min_length=42,
        help_text="Ethereum wallet address (42 characters, starting with 0x)",
    )

    def validate_wallet_address(self, value):
        if not value.startswith("0x"):
            raise serializers.ValidationError("Wallet address must start with '0x'")
        try:
            int(value[2:], 16)
        except ValueError:
            raise serializers.ValidationError("Invalid hexadecimal address")
        return value
