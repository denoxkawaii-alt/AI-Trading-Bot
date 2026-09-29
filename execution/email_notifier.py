import logging
from typing import Optional

import requests

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


def send_email(subject: str, text: str, html: Optional[str] = None) -> bool:
    """Send a transactional email through Resend. Missing credentials fail closed."""
    api_key = SETTINGS.RESEND_API_KEY.strip()
    recipient = SETTINGS.EMAIL_TO.strip()
    sender = SETTINGS.EMAIL_FROM.strip()

    if not api_key or not recipient or not sender:
        logger.info("Email credentials not configured. Skipping email alert.")
        return False

    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html

    try:
        response = requests.post(
            _RESEND_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("id"):
            logger.error("Resend email response did not contain an email id: %s", data)
            return False
        logger.info("Email alert sent to %s (id=%s).", recipient, data["id"])
        return True
    except (requests.RequestException, ValueError) as exc:
        logger.error("Email alert failed: %s", exc)
        return False


def trade_email(
    symbol: str,
    side: str,
    entry: float,
    stop_loss: float,
    target: float,
    quantity: int,
    risk: float,
    risk_reward: float,
    mc_probability: Optional[float] = None,
    vwap: Optional[float] = None,
    volume: Optional[float] = None,
    vsa_required_volume: Optional[float] = None,
) -> bool:
    lines = [
        "📊 PAPER TRADE",
        "",
        f"Symbol: {symbol}",
        f"Side: {side}",
        f"Entry: ₹{entry:.2f}",
        f"Stop Loss: ₹{stop_loss:.2f}",
        f"Target: ₹{target:.2f}",
        f"Quantity: {quantity}",
        f"Risk: ₹{risk:.2f}",
        f"R:R: 1:{risk_reward:.2f}",
    ]
    if mc_probability is not None:
        lines.append(f"MC Probability: {mc_probability:.1f}%")
    if vwap is not None:
        lines.append(f"VWAP: ₹{vwap:.2f}")
    if volume is not None:
        lines.append(f"Breakout Volume: {volume:.0f}")
    if vsa_required_volume is not None:
        lines.append(f"VSA Required Volume: {vsa_required_volume:.0f}")
    lines += ["", "Mode: PAPER ONLY", "Broker order: NOT SENT"]

    return send_email(
        subject=f"AI Trading Bot | PAPER {side} | {symbol}",
        text="\n".join(lines),
    )


def exit_email(
    symbol: str,
    side: str,
    quantity: int,
    entry: float,
    exit_price: float,
    pnl: float,
    reason: str,
) -> bool:
    text = "\n".join([
        "📕 PAPER TRADE EXIT",
        "",
        f"Symbol: {symbol}",
        f"Side: {side}",
        f"Quantity: {quantity}",
        f"Entry: ₹{entry:.2f}",
        f"Exit: ₹{exit_price:.2f}",
        f"Reason: {reason}",
        f"P&L: ₹{pnl:.2f}",
        "",
        "Mode: PAPER ONLY",
        "Broker order: NOT SENT",
    ])
    return send_email(
        subject=f"AI Trading Bot | PAPER EXIT | {symbol} | {reason}",
        text=text,
    )
