from django.db import models


class Transaction(models.Model):
    wallet_address = models.CharField(max_length=42)
    transaction_hash = models.CharField(max_length=66)
    amount = models.DecimalField(max_digits=18, decimal_places=18)
    status = models.CharField(max_length=10)  # 'success' or 'failed'
    error_message = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet_address} {self.amount} {self.created_at} - {self.status}"
