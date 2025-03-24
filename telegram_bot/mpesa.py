import base64
import datetime
import requests
from django.conf import settings

# M-Pesa API URL for STK Push
MPESA_API_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"


# Function to get M-Pesa OAuth token
def get_mpesa_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    headers = {
        "Authorization": "Basic " + base64.b64encode(
            f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode('utf-8')).decode('utf-8')
    }
    response = requests.get(url, headers=headers)
    token = response.json().get('access_token')
    return token


# Function to initiate STK Push payment request
def initiate_mpesa_payment(phone_number, amount):
    token = get_mpesa_token()  # Get the access token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Get current timestamp in the required format
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    # M-Pesa API request body
    data = {
        "BusinessShortcode": settings.MPESA_SHORTCODE,
        "Password": settings.MPESA_PASSWORD,  # Provided by Safaricom
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,  # Customer's phone number
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": f"{settings.BASE_URL}/mpesa/payment_callback/",  # Your callback URL
        "AccountReference": "MealPlan1234",
        "TransactionDesc": "Payment for meal plan subscription"
    }

    # Send POST request to initiate STK Push
    response = requests.post(MPESA_API_URL, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()  # Return M-Pesa's response
    else:
        return {"error": response.json()}
