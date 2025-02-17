from rest_framework import serializers
from .models import Transaction


class WalletAddressSerializer(serializers.Serializer):
    wallet_address = serializers.CharField(max_length=42)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class StatsSerializer(serializers.Serializer):
    successful_transactions = serializers.IntegerField()
    failed_transactions = serializers.IntegerField()
