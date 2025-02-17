from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("wallet_address", models.CharField(max_length=42)),
                ("transaction_hash", models.CharField(max_length=66)),
                ("amount", models.DecimalField(decimal_places=18, max_digits=18)),
                ("status", models.CharField(max_length=10)),
                ("error_message", models.TextField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
