import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from django.conf import settings
from .mpesa import initiate_mpesa_payment

# Initialize the Telegram Bot with the token from settings
bot = Bot(token=settings.TELEGRAM_TOKEN)
dispatcher = Application.builder().token(settings.TELEGRAM_TOKEN).build()

# Command to start the bot and show options to the user
def start(update, context):
    update.message.reply_text(
        "Hello and welcome to [Your Fitness Brand] Meal Plans! 🌟\n\n"
        "I’m here to help you find the perfect meal plan to match your fitness goals. Please choose one of the following plans by typing the corresponding number:\n"
        "1. Weight Loss Plan\n"
        "2. Muscle Gain Plan\n"
        "3. Balanced Diet Plan\n\n"
        "Just type 1, 2, or 3 to get started!"
    )

# Handle message for meal plan selection
def handle_message(update, context):
    text = update.message.text.lower()
    if text == "1":
        update.message.reply_text(
            "You’ve selected the **Weight Loss Plan**! 🎯\n\n"
            "This plan includes:\n"
            "- 7 days of calorie-controlled meals.\n"
            "- Nutritional guidance to help you stay on track.\n"
            "- Easy-to-prepare recipes for busy schedules.\n\n"
            "Price: KSH 1000 for one week.\n\n"
            "To proceed with payment, please input your **Safaricom phone number** (the number associated with your M-Pesa account)."
        )
    elif text == "2":
        update.message.reply_text("Selected Muscle Gain Plan!")
    elif text == "3":
        update.message.reply_text("Selected Balanced Diet Plan!")
    else:
        update.message.reply_text("Please choose a valid plan: 1, 2, or 3.")

# Payment initiation (after Safaricom number input)
def payment(update, context):
    phone_number = update.message.text
    # Call M-Pesa API to initiate STK Push with phone_number
    payment_status = initiate_mpesa_payment(phone_number, amount=1)  # Adjust amount as needed

    if payment_status.get("error"):
        update.message.reply_text(f"Payment failed: {payment_status['error']}")
    else:
        update.message.reply_text("Payment successful! Here's your plan:\n[Meal Plan PDF] [Link to VIP Channel]")

# Webhook view to receive messages from Telegram
@csrf_exempt
def webhook(request):
    if request.method == "POST":
        json_str = request.body.decode("UTF-8")
        update = Update.de_json(json_str, bot)
        dispatcher.process_update(update)
        return JsonResponse({"status": "ok"})
    else:
        return JsonResponse({"status": "failed"}, status=400)

# M-Pesa Payment Callback
@csrf_exempt
def payment_callback(request):
    if request.method == "POST":
        try:
            # Parse M-Pesa callback data
            response_data = json.loads(request.body.decode('utf-8'))
            transaction_status = response_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')

            if transaction_status == 0:  # Success
                phone_number = response_data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [{}])[0].get('Value')
                amount = response_data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [{}])[1].get('Value')

                # Process successful payment here
                update_user_payment_status(phone_number, amount)

                return JsonResponse({"status": "success", "message": "Payment confirmed."})
            else:
                return JsonResponse({"status": "failed", "message": "Payment failed."})

        except Exception as e:
            return JsonResponse({"status": "failed", "message": str(e)}, status=500)

    return JsonResponse({"status": "failed", "message": "Invalid request."}, status=400)

# Function to update user payment status (you can integrate this with your database)
def update_user_payment_status(phone_number, amount):
    pass  # Implement logic to update the user's status in the database
