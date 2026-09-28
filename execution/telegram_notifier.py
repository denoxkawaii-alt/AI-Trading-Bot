import requests
from config.settings import SETTINGS
def send_alert(message):
 if not SETTINGS.TELEGRAM_BOT_TOKEN or not SETTINGS.TELEGRAM_CHAT_ID:return False
 r=requests.post(f"https://api.telegram.org/bot{SETTINGS.TELEGRAM_BOT_TOKEN}/sendMessage",json={"chat_id":SETTINGS.TELEGRAM_CHAT_ID,"text":message},timeout=15); r.raise_for_status(); return True
def trade_alert(symbol,p):return send_alert(f"📊 PAPER TRADE\n{symbol} {p.side}\nEntry ₹{p.entry:.2f}\nSL ₹{p.stop:.2f}\nTarget ₹{p.target:.2f}\nQty {p.quantity}\nRisk ₹{p.risk_rupees:.2f}\nRR 1:{p.rr:.2f}\nMC {p.mc_probability:.1%}")