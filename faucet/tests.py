from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from web3 import Web3
from web3.exceptions import TransactionNotFound
from faucet.models import Transaction
from django.utils import timezone
from datetime import timedelta


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
@patch("django.db.models.Model.save", MagicMock())
@patch("django.db.models.Model.delete", MagicMock())
class FaucetAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.enforce_csrf_checks = False
        self.fund_url = reverse("faucet-fund")
        self.stats_url = reverse("faucet-stats")
        self.valid_wallet = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        self.test_tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        # Mock Transaction model
        self.transaction_patcher = patch("faucet.views.Transaction")
        self.mock_transaction = self.transaction_patcher.start()
        self.mock_transaction.objects = MagicMock()

        # Mock rate limiter
        self.ratelimit_patcher = patch("faucet.views.ratelimit")
        self.mock_ratelimit = self.ratelimit_patcher.start()
        self.mock_ratelimit.return_value = lambda func: func

        # Mock Web3
        self.web3_patcher = patch("faucet.views.Web3")
        self.mock_web3 = self.web3_patcher.start()
        self.mock_eth = MagicMock()
        self.mock_web3.HTTPProvider.return_value = MagicMock()
        self.mock_web3.return_value.eth = self.mock_eth

        # Mock serializer
        self.serializer_patcher = patch("faucet.views.WalletAddressSerializer")
        self.mock_serializer = self.serializer_patcher.start()
        self.mock_serializer.return_value = MagicMock()

    def tearDown(self):
        self.transaction_patcher.stop()
        self.ratelimit_patcher.stop()
        self.web3_patcher.stop()
        self.serializer_patcher.stop()

    def test_fund_success(self):
        """Test successful ETH funding request"""
        # Mock serializer validation
        self.mock_serializer.return_value.is_valid.return_value = True
        self.mock_serializer.return_value.validated_data = {
            "wallet_address": self.valid_wallet
        }

        # Mock Web3 responses
        self.mock_eth.gas_price = 20000000000
        self.mock_eth.get_transaction_count.return_value = 1
        tx_hash_bytes = Web3.to_bytes(hexstr=self.test_tx_hash)
        self.mock_eth.send_raw_transaction.return_value = tx_hash_bytes

        # Mock no recent transactions
        self.mock_transaction.objects.filter.return_value.exists.return_value = False

        response = self.client.post(
            self.fund_url, {"wallet_address": self.valid_wallet}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["transaction_hash"], self.test_tx_hash[2:]
        )  # Compare without '0x'
        self.mock_transaction.objects.create.assert_called_once()

    def test_fund_invalid_wallet(self):
        """Test funding request with invalid wallet address"""
        # Mock serializer validation failure
        self.mock_serializer.return_value.is_valid.return_value = False
        self.mock_serializer.return_value.errors = {
            "wallet_address": ["Invalid wallet address"]
        }

        response = self.client.post(
            self.fund_url, {"wallet_address": "invalid_address"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mock_transaction.objects.create.assert_not_called()

    def test_fund_rate_limited(self):
        """Test rate limiting for repeated requests"""
        # Mock recent successful transaction
        self.mock_transaction.objects.filter.return_value.exists.return_value = True

        response = self.client.post(
            self.fund_url, {"wallet_address": self.valid_wallet}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("error", response.data)
        self.mock_transaction.objects.create.assert_not_called()

    def test_fund_transaction_failure(self):
        """Test handling of failed blockchain transaction"""
        # Mock Web3 error
        self.mock_eth.send_raw_transaction.side_effect = TransactionNotFound(
            "Transaction failed"
        )

        # Mock no recent transactions
        self.mock_transaction.objects.filter.return_value.exists.return_value = False

        response = self.client.post(
            self.fund_url, {"wallet_address": self.valid_wallet}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        # Verify failed transaction was recorded
        self.mock_transaction.objects.create.assert_called_once()

    def test_stats_success(self):
        """Test successful stats retrieval"""
        # Mock transaction statistics
        self.mock_transaction.objects.count.return_value = 100
        self.mock_transaction.objects.filter.return_value.count.return_value = 50

        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_transactions"], 100)
        self.assertEqual(response.data["last_24h_transactions"], 50)
        self.assertEqual(response.data["successful_transactions"], 50)
        self.assertEqual(response.data["failed_transactions"], 50)

    def test_stats_empty(self):
        """Test stats retrieval with no transactions"""
        # Mock empty transaction data
        self.mock_transaction.objects.count.return_value = 0
        self.mock_transaction.objects.filter.return_value.count.return_value = 0

        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_transactions"], 0)
        self.assertEqual(response.data["last_24h_transactions"], 0)
        self.assertEqual(response.data["successful_transactions"], 0)
        self.assertEqual(response.data["failed_transactions"], 0)


class TransactionListTests(APITestCase):
    def setUp(self):
        # Create transaction1 (newer)
        self.now = timezone.now()
        self.transaction1 = Transaction.objects.create(
            transaction_hash="0x123",
            wallet_address="0xabc",
            amount=0.1,
            status="success",
            ip_address="127.0.0.1",
        )

        # Create transaction2 (older)
        one_day_ago = self.now - timedelta(days=1)
        self.transaction2 = Transaction.objects.create(
            transaction_hash="0x456",
            wallet_address="0xdef",
            amount=0.2,
            status="failed",
            ip_address="127.0.0.1",
        )

        # Manually update created_at fields
        Transaction.objects.filter(pk=self.transaction1.pk).update(created_at=self.now)
        Transaction.objects.filter(pk=self.transaction2.pk).update(
            created_at=one_day_ago
        )

    def test_list_all_transactions(self):
        """Test retrieving all transactions without filters"""
        url = reverse("transaction-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Verify the most recent transaction is first
        self.assertEqual(response.data[0]["transaction_hash"], "0x123")
        self.assertEqual(response.data[1]["transaction_hash"], "0x456")

    def test_filter_by_wallet(self):
        """Test filtering transactions by wallet address"""
        url = reverse("transaction-list")
        response = self.client.get(url, {"wallet": "0xabc"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["wallet_address"], "0xabc")

    def test_filter_by_date_range(self):
        """Test filtering transactions by date range"""
        from_date = (self.now - timedelta(minutes=5)).isoformat()
        to_date = (self.now + timedelta(minutes=5)).isoformat()

        url = reverse("transaction-list")
        response = self.client.get(url, {"from_date": from_date, "to_date": to_date})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["transaction_hash"], "0x123")

    def test_invalid_date_format(self):
        """Test invalid date format returns 400"""
        url = reverse("transaction-list")
        response = self.client.get(url, {"from_date": "invalid-date"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_combined_filters(self):
        """Test combining multiple filters"""
        now = timezone.now()
        from_date = (now - timedelta(hours=12)).isoformat()

        url = reverse("transaction-list")
        response = self.client.get(url, {"from_date": from_date, "wallet": "0xabc"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["transaction_hash"], "0x123")
        self.assertEqual(response.data[0]["wallet_address"], "0xabc")
