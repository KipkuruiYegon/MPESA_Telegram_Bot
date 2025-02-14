from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import requests
from django.conf import settings
from payments.models import TelegramUser, Transaction
import os



bot = Bot(token=TOKEN)


# Check if user has joined the channel
def check_subscription(user_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={CHANNEL_USERNAME}&user_id={user_id}"
    response = requests.get(url).json()
    status = response.get("result", {}).get("status")
    return status in ["member", "administrator", "creator"]


# Command: /start
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    user, created = TelegramUser.objects.get_or_create(user_id=user_id, defaults={"username": username})

    if not check_subscription(user_id):
        update.message.reply_text(f"🚨 You must join {CHANNEL_USERNAME} before making a payment.")
        return

    update.message.reply_text("✅ Welcome! Use /pay <phone_number> <amount> to make a payment.")


# Command: /pay <phone_number> <amount>
def pay(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not check_subscription(user_id):
        update.message.reply_text("❌ You need to join the channel first.")
        return

    args = context.args
    if len(args) != 2:
        update.message.reply_text("Usage: /pay <phone_number> <amount>")
        return

    phone, amount = args
    user = TelegramUser.objects.get(user_id=user_id)
    transaction = Transaction.objects.create(user=user, phone_number=phone, amount=amount)

    # Initiate STK Push
    access_token = get_mpesa_access_token()
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": "GENERATED_PASSWORD",
        "Timestamp": "YYYYMMDDHHMMSS",
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://yourdomain.com/mpesa/callback",
        "AccountReference": "Subscription",
        "TransactionDesc": "Subscription Payment"
    }

    response = requests.post(url, json=payload, headers=headers)
    transaction.transaction_id = response.json().get("CheckoutRequestID", "")
    transaction.save()

    update.message.reply_text(f"✅ Payment request sent to {phone}. Approve on your phone!")


# Get M-Pesa Access Token
def get_mpesa_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    headers = {"Authorization": f"Basic {os.getenv('MPESA_AUTH')}"}
    response = requests.get(url, headers=headers)
    return response.json().get("access_token")


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("pay", pay))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
