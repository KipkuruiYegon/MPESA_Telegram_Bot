from django.db import models

class TelegramUser(models.Model):
    user_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.username or str(self.user_id)

class Transaction(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount} KES"
