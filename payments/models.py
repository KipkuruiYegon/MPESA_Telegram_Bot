from django.db import models

# Create your models here.

class TelegramUser(models.Model):
    user_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    joined_channel = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)

class Transaction(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Failed', 'Failed')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
