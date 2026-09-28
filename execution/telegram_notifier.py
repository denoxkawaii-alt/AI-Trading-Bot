import logging
from typing import Optional
import requests
from config.settings import SETTINGS

logger = logging.getLogger(__name__)

def send_alert(message: str) -> bool:
    token = SETTINGS.TELEGRAM_BOT_TOKEN.strip()
    chat_id = SETTINGS.TELEGRAM_CHAT_ID.strip()
    if not token or not chat_id:
        logger.info("Telegram credentials not configured. Skipping alert.")
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message}, timeout=15)
        r.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error("Telegram alert failed: %s", exc)
        return False

def trade_alert(symbol: str, side: str, entry: float, stop_loss: float, target: float, quantity: int,
                risk: float, risk_reward: float, mc_probability: Optional[float] = None,
                vwap: Optional[float] = None, volume: Optional[float] = None,
                vsa_required_volume: Optional[float] = None) -> bool:
    lines = ["📊 PAPER TRADE", "", f"Symbol: {symbol}", f"Side: {side}", f"Entry: ₹{entry:.2f}",
             f"Stop Loss: ₹{stop_loss:.2f}", f"Target: ₹{target:.2f}", f"Quantity: {quantity}",
             f"Risk: ₹{risk:.2f}", f"R:R: 1:{risk_reward:.2f}"]
    if mc_probability is not None: lines.append(f"MC Probability: {mc_probability:.1f}%")
    if vwap is not None: lines.append(f"VWAP: ₹{vwap:.2f}")
    if volume is not None: lines.append(f"Breakout Volume: {volume:.0f}")
    if vsa_required_volume is not None: lines.append(f"VSA Required Volume: {vsa_required_volume:.0f}")
    lines += ["", "Mode: PAPER ONLY", "Broker order: NOT SENT"]
    return send_alert("\n".join(lines))

def exit_alert(symbol: str, side: str, quantity: int, entry: float, exit_price: float,
               pnl: float, reason: str) -> bool:
    return send_alert("\n".join([
        "📕 PAPER TRADE EXIT", "", f"Symbol: {symbol}", f"Side: {side}",
        f"Quantity: {quantity}", f"Entry: ₹{entry:.2f}", f"Exit: ₹{exit_price:.2f}",
        f"Reason: {reason}", f"P&L: ₹{pnl:.2f}", "", "Mode: PAPER ONLY", "Broker order: NOT SENT"
    ]))
