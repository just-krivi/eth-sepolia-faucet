from django.db import models

STATUS_CHOICES = [
    ("success", "Success"),
    ("failed", "Failed"),
]


class Transaction(models.Model):
    wallet_address = models.CharField(max_length=42)
    transaction_hash = models.CharField(max_length=66)
    amount = models.DecimalField(max_digits=18, decimal_places=9)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    error_message = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=True)

    def __str__(self):
        return f"{self.wallet_address} {self.amount} {self.created_at} - {self.status}"
