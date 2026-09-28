import requests
from config.settings import SETTINGS

def send_alert(message):
    if not SETTINGS.TELEGRAM_BOT_TOKEN or not SETTINGS.TELEGRAM_CHAT_ID:return False
    r=requests.post(f"https://api.telegram.org/bot{SETTINGS.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id":SETTINGS.TELEGRAM_CHAT_ID,"text":message},timeout=15)
    r.raise_for_status(); return True

def trade_alert(symbol,plan):
    return send_alert(f"📊 PAPER TRADE\n{symbol} {plan.side}\nEntry ₹{plan.entry:.2f}\nSL ₹{plan.stop:.2f}\nTarget ₹{plan.target:.2f}\nQty {plan.quantity}\nRisk ₹{plan.risk_rupees:.2f}\nRR 1:{plan.rr:.2f}\nMC {plan.mc_probability:.1%}")
