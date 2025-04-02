import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Bot, Update
from django.conf import settings
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from .mpesa import initiate_mpesa_payment  # Make sure this method exists and does not cause circular imports

# Initialize the Telegram Bot with the token from settings
bot = Bot(token=settings.TELEGRAM_TOKEN)

# Initialize the Application correctly using Application.builder
application = Application.builder().token(settings.TELEGRAM_TOKEN).build()

# Command to start the bot and show options to the user
async def start(update, context):
    await update.message.reply_text(
        "Hello and welcome to [Your Fitness Brand] Meal Plans! 🌟\n\n"
        "I’m here to help you find the perfect meal plan to match your fitness goals. Please choose one of the following plans by typing the corresponding number:\n"
        "1. Weight Loss Plan\n"
        "2. Muscle Gain Plan\n"
        "3. Balanced Diet Plan\n\n"
        "Just type 1, 2, or 3 to get started!"
    )

# Handle message for meal plan selection
async def handle_message(update, context):
    text = update.message.text.lower()
    if text == "1":
        await update.message.reply_text(
            "You’ve selected the **Weight Loss Plan**! 🎯\n\n"
            "This plan includes:\n"
            "- 7 days of calorie-controlled meals.\n"
            "- Nutritional guidance to help you stay on track.\n"
            "- Easy-to-prepare recipes for busy schedules.\n\n"
            "Price: KSH 1000 for one week.\n\n"
            "To proceed with payment, please input your **Safaricom phone number** (the number associated with your M-Pesa account)."
        )
    elif text == "2":
        await update.message.reply_text("Selected Muscle Gain Plan!")
    elif text == "3":
        await update.message.reply_text("Selected Balanced Diet Plan!")
    else:
        await update.message.reply_text("Please choose a valid plan: 1, 2, or 3.")

# Payment initiation (after Safaricom number input)
async def payment(update, context):
    phone_number = update.message.text
    # Call M-Pesa API to initiate STK Push with phone_number
    payment_status = initiate_mpesa_payment(phone_number, amount=1)  # Adjust amount as needed

    if payment_status.get("error"):
        await update.message.reply_text(f"Payment failed: {payment_status['error']}")
    else:
        await update.message.reply_text("Payment successful! Here's your plan:\n[Meal Plan PDF] [Link to VIP Channel]")

# Webhook view to receive messages from Telegram
@csrf_exempt
async def webhook(request):
    if request.method == "POST":
        json_str = request.body.decode("UTF-8")
        try:
            update_data = json.loads(json_str)
            update = Update.de_json(update_data, bot)  # Ensure 'bot' is defined
            await application.process_update(update)  # Use 'application' to process the update
            return JsonResponse({"status": "ok"})
        except Exception as e:
            print(f"Error processing update: {e}")
            return JsonResponse({"status": "failed", "message": str(e)}, status=400)
    else:
        return JsonResponse({"status": "failed"}, status=400)

# M-Pesa Payment Callback
@csrf_exempt
async def payment_callback(request):
    print("Received callback request:", request.body)  # Debugging line
    if request.method == "POST":
        try:
            response_data = json.loads(request.body.decode('utf-8'))
            transaction_status = response_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')

            if transaction_status == 0:  # Success
                phone_number = response_data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [{}])[0].get('Value')
                amount = response_data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [{}])[1].get('Value')

                update_user_payment_status(phone_number, amount)
                return JsonResponse({"status": "success", "message": "Payment confirmed."})
            else:
                return JsonResponse({"status": "failed", "message": "Payment failed."})

        except Exception as e:
            return JsonResponse({"status": "failed", "message": str(e)}, status=500)

    return JsonResponse({"status": "failed", "message": "Invalid request."}, status=400)

def update_user_payment_status(phone_number, amount):
    pass  # Implement logic to update the user's status in the database

# Initialize bot commands
async def initialize_bot():
    # Add the handler for /start and message handling
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Set webhook for the Telegram bot
    await bot.set_webhook(url="https://6954-105-163-2-235.ngrok-free.app/telegram/webhook/")

# Run the bot asynchronously
if __name__ == '__main__':
    initialize_bot()  # Make sure to initialize your bot properly
