from binance.client import Client
from config import API_KEY, API_SECRET

client = Client(API_KEY, API_SECRET)

try:
    account = client.get_account()
    print("✅ Binance Connected Successfully!")
    print("Account Type:", account["accountType"])
except Exception as e:
    print("❌ Connection Failed")
    print(type(e).__name__)
