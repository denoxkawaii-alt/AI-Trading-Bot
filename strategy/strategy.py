from binance.client import Client
from config import API_KEY, API_SECRET
from ta.momentum import RSIIndicator
import pandas as pd
client = Client(API_KEY, API_SECRET)

def get_signal():
    try:
        candles = client.get_klines(
            symbol="BTCUSDT",
            interval=Client.KLINE_INTERVAL_1MINUTE,
            limit=20
        
        closes = [float(c[4]) for c in candles]
df =     pd.DataFrame(closes, columns=["close"])
rsi =    RSIIndicator(df["close"], window=14).rsi().iloc[-1]
        ema9 = sum(closes[-9:]) / 9
        ema20 = sum(closes) / 20

        if ema9 > ema20:
            signal = "BUY"
        else:
            signal = "SELL"

        return {
            "signal": signal,
            "confidence": 80,
            "reason": f"EMA9={ema9:.2f} EMA20={ema20:.2f}"
        }

    except Exception as e:
        return {
            "signal": "HOLD",
            "confidence": 0,
            "reason": str(e)
        }
