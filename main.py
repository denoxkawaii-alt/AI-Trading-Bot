from strategy.strategy import get_signal

print("=" * 40)
print("AI Trading Bot")
print("Version 1.1")
print("=" * 40)

signal = get_signal()

print("Signal      :", signal["signal"])
print("Confidence  :", signal["confidence"])
print("Reason      :", signal["reason"])
