import requests
from requests.auth import HTTPBasicAuth

MPESA_CONSUMER_KEY = "pJiFFoA4sOOvP9V2XnVL6ommgXUXm9FhGCQNAelkj3tn3ciX"
MPESA_CONSUMER_SECRET = "p7SMlbLfEENJ8kIzAqbI5qpzCBCC0foXtPufF2zMXWOBs7doDgKnTFeTrvWeW0u3"
MPESA_AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

response = requests.get(
    MPESA_AUTH_URL,
    auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET)
)

print(response.json())
