import requests
import base64
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from payments.models import TelegramUser, Transaction
from bot_project.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_USERNAME,
    TELEGRAM_CHANNEL_ID,
    MPESA_CONSUMER_KEY,
    MPESA_CONSUMER_SECRET,
    MPESA_SHORTCODE,
    MPESA_PASSKEY,
    MPESA_CALLBACK_URL
)

# Set up logging
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)


# ✅ 1. Check if user is subscribed
async def check_subscription(user_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember?chat_id={TELEGRAM_CHANNEL_ID}&user_id={user_id}"
    response = requests.get(url).json()
    print(response)  # Debugging output
    status = response.get("result", {}).get("status")
    return status in ["member", "administrator", "creator"]


# ✅ 2. Generate M-Pesa Access Token
def get_mpesa_access_token():
    credentials = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {encoded_credentials}"}
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        logging.error("Failed to get M-Pesa access token: %s", response.text)
        return None


# ✅ 3. Generate Password and Timestamp for STK Push
def generate_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
    return base64.b64encode(password).decode(), timestamp


# ✅ 4. Grant Telegram access after payment
async def grant_access(user_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/inviteChatMember"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "user_id": user_id
    }
    response = requests.post(url, json=payload).json()
    logging.info(f"Grant access response: {response}")


# ✅ 5. Start Command Handler
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    user, _ = TelegramUser.objects.get_or_create(user_id=user_id, defaults={"username": username})

    if not await check_subscription(user_id):
        await update.message.reply_text(f"🚨 You must join {TELEGRAM_CHANNEL_USERNAME} before making a payment.")
        return

    await update.message.reply_text("✅ Welcome! Use /pay <phone_number> <amount> to make a payment.")


# ✅ 6. Payment Command Handler
async def pay(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not await check_subscription(user_id):
        await update.message.reply_text("❌ You need to join the channel first.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /pay <phone_number> <amount>")
        return

    phone, amount = args
    user = TelegramUser.objects.get(user_id=user_id)

    # Validate Amount
    try:
        amount = int(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a positive number.")
        return

    transaction = Transaction.objects.create(user=user, phone_number=phone, amount=amount)

    # Get M-Pesa Access Token
    access_token = get_mpesa_access_token()
    if not access_token:
        await update.message.reply_text("❌ Payment service is unavailable. Try again later.")
        return

    # Generate Password & Timestamp
    password, timestamp = generate_password()

    # Initiate STK Push
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": "Subscription",
        "TransactionDesc": "Subscription Payment"
    }

    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()

    if "CheckoutRequestID" in response_data:
        transaction.transaction_id = response_data["CheckoutRequestID"]
        transaction.save()
        await update.message.reply_text(f"✅ Payment request sent to {phone}. Approve on your phone!")
    else:
        logging.error("STK Push Error: %s", response.text)
        await update.message.reply_text("❌ Payment request failed. Try again later.")


# ✅ 7. Payment Status Checker
async def status(update: Update, context: CallbackContext):
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /status <transaction_id>")
        return

    transaction_id = args[0]
    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
        status_msg = f"📋 Transaction Status:\n" \
                     f"🆔 Transaction ID: {transaction.transaction_id}\n" \
                     f"📱 Phone: {transaction.phone_number}\n" \
                     f"💰 Amount: {transaction.amount}\n" \
                     f"✅ Status: {'Completed' if transaction.is_paid else 'Pending'}"
        await update.message.reply_text(status_msg)
    except Transaction.DoesNotExist:
        await update.message.reply_text("❌ Transaction not found.")


# ✅ 8. M-Pesa Callback Handling
@csrf_exempt
def mpesa_callback(request):
    data = request.json()
    logging.info("Received M-Pesa Callback: %s", data)

    try:
        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        transaction_id = body.get("CheckoutRequestID")

        # Find transaction
        transaction = Transaction.objects.get(transaction_id=transaction_id)

        if result_code == 0:
            transaction.is_paid = True
            transaction.save()

            # Grant Telegram access
            bot.loop.run_until_complete(grant_access(transaction.user.user_id))

            message = f"✅ Payment Successful!\n" \
                      f"💰 Amount: {transaction.amount}\n" \
                      f"📱 Phone: {transaction.phone_number}"
        else:
            message = "❌ Payment Failed."

        bot.send_message(chat_id=transaction.user.user_id, text=message)

        return JsonResponse({"status": "success"})
    except Exception as e:
        logging.error("Callback Error: %s", str(e))
        return JsonResponse({"status": "error"}, status=500)


# ✅ 9. Main Function
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("status", status))
    await app.run_polling()


# Run the bot
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
