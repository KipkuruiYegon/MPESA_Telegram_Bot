import os
import requests
import base64
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# M-Pesa Credentials
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = "174379"
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
CALLBACK_URL = "https://your-free-host.com/mpesa/callback"

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_mpesa_token():
    """Fetch M-Pesa API token with error handling"""
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("❌ Failed to get M-Pesa Token:", response.json())  # Debugging
        return None

def generate_mpesa_password():
    """Generate M-Pesa STK push password"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    data_to_encode = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    encoded_password = base64.b64encode(data_to_encode.encode()).decode()
    return encoded_password, timestamp

@app.route('/stk_push', methods=['POST'])
def stk_push():
    """Initiate STK Push"""
    data = request.json
    phone_number = data.get("phone")
    amount = data.get("amount")

    if not phone_number or not amount:
        return jsonify({"error": "Missing phone number or amount"}), 400

    token = get_mpesa_token()
    if not token:
        return jsonify({"error": "Failed to get M-Pesa token"}), 500

    password, timestamp = generate_mpesa_password()

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "Gym Payment",
        "TransactionDesc": "Fitness Training Fee"
    }

    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload, headers=headers
    )

    return jsonify(response.json())

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa Payment Callback"""
    data = request.json
    print("M-Pesa Response:", data)  # Debugging

    # Extract payment details
    body = data.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode", -1)
    result_desc = body.get("ResultDesc", "Unknown Error")
    amount = 0
    phone_number = "Unknown"

    if result_code == 0:
        callback_metadata = body.get("CallbackMetadata", {}).get("Item", [])
        for item in callback_metadata:
            if item["Name"] == "Amount":
                amount = item["Value"]
            if item["Name"] == "PhoneNumber":
                phone_number = item["Value"]

    # Format Telegram Message
    if result_code == 0:
        message = f"✅ Payment Received! Amount: KES {amount}\n📞 Phone: {phone_number}"
    else:
        message = f"❌ Payment Failed: {result_desc}"

    # Send Telegram Notification
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(telegram_url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

    return jsonify({"status": "Received"}), 200

if __name__ == "__main__":
    app.run(debug=True)
