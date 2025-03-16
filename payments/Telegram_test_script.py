import requests

BOT_TOKEN = "7818790241:AAFB7a02h4DIKjNuiwYavefzJ1W4xfo5h-0"
CHANNEL_ID = "-1002562564483"
MESSAGE = "🚀 MTB Payment Bot is live!"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
data = {"chat_id": CHANNEL_ID, "text": MESSAGE}

response = requests.post(url, data=data)
print(response.json())
