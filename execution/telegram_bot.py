import csv
import logging
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, payload: Optional[dict] = None, timeout: int = 20) -> Optional[dict]:
    try:
        response = requests.post(
            _API.format(token=token, method=method),
            json=payload or {},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            logger.error("Telegram API %s failed: %s", method, data)
            return None
        return data
    except (requests.RequestException, ValueError) as exc:
        logger.error("Telegram API %s error: %s", method, exc)
        return None


def send_message(token: str, chat_id: str, text: str) -> bool:
    return _call(token, "sendMessage", {"chat_id": chat_id, "text": text}, timeout=15) is not None


class TelegramCommandBot:
    """Small dependency-free Telegram command poller for the paper-trading worker."""

    def __init__(self, trader, data_dir: str):
        self.trader = trader
        self.data_dir = Path(data_dir)
        self.token = SETTINGS.TELEGRAM_BOT_TOKEN.strip()
        self.allowed_chat_id = SETTINGS.TELEGRAM_CHAT_ID.strip()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not self.token or not self.allowed_chat_id:
            logger.info("Telegram command bot disabled: credentials not configured.")
            return
        # Polling and a Telegram webhook cannot be active at the same time. Clear any
        # stale webhook so getUpdates can receive commands after a redeploy.
        webhook = _call(self.token, "deleteWebhook", {"drop_pending_updates": False}, timeout=15)
        if webhook is None:
            logger.warning("Telegram webhook cleanup failed; polling may return 409 until it is cleared.")
        self._thread = threading.Thread(target=self._poll, name="telegram-command-bot", daemon=True)
        self._thread.start()
        logger.info("Telegram command bot started.")

    def stop(self) -> None:
        self._stop.set()

    def _reply(self, chat_id: str, message: str) -> None:
        send_message(self.token, chat_id, message)

    def _status(self) -> str:
        return (
            "🤖 AI Trading Bot\n\n"
            "Status: ACTIVE\n"
            "Mode: PAPER ONLY\n"
            "Broker orders: NOT SENT\n"
            f"Open positions: {len(self.trader.positions)}\n"
            f"Today's trades: {self.trader.daily_trade_count}/{self.trader.max_daily_trades}\n"
            f"Equity: ₹{self.trader.get_equity():.2f}"
        )

    def _portfolio(self) -> str:
        if not self.trader.positions:
            return (
                "📊 PAPER PORTFOLIO\n\n"
                "No open positions.\n"
                f"Equity: ₹{self.trader.get_equity():.2f}"
            )
        lines = ["📊 PAPER PORTFOLIO", ""]
        for position in list(self.trader.positions.values()):
            lines.extend([
                f"• {position.symbol} {position.side}",
                f"  Qty: {position.quantity}",
                f"  Entry: ₹{position.entry:.2f}",
                f"  SL: ₹{position.stop_loss:.2f}",
                f"  Target: ₹{position.target:.2f}",
                "",
            ])
        lines.append(f"Equity: ₹{self.trader.get_equity():.2f}")
        return "\n".join(lines)

    def _trades(self) -> str:
        path = self.data_dir / "trades.csv"
        if not path.exists():
            return "📜 TRADES\n\nNo trades recorded yet."
        try:
            with path.open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except OSError as exc:
            logger.error("Could not read trade ledger: %s", exc)
            return "📜 TRADES\n\nTrade ledger is temporarily unavailable."
        if not rows:
            return "📜 TRADES\n\nNo closed trades yet."
        lines = ["📜 LAST TRADES", ""]
        for row in rows[-5:][::-1]:
            pnl = row.get("pnl", "0")
            try:
                pnl_text = f"₹{float(pnl):.2f}"
            except (TypeError, ValueError):
                pnl_text = str(pnl)
            lines.append(
                f"{row.get('symbol', '?')} | {row.get('side', '?')} | "
                f"Entry ₹{row.get('entry', '?')} → Exit ₹{row.get('exit', '?')} | P&L {pnl_text}"
            )
        return "\n".join(lines)

    def _handle(self, chat_id: str, text: str) -> None:
        if str(chat_id) != self.allowed_chat_id:
            logger.warning("Ignoring Telegram command from unauthorized chat %s.", chat_id)
            return
        command = (text or "").strip().split()[0].lower() if text else ""
        if "@" in command:
            command = command.split("@", 1)[0]
        if command in {"/start", "/help"}:
            self._reply(chat_id, (
                "🤖 Kakashi AI Trading Bot\n\n"
                "Bot is connected and running in PAPER mode.\n\n"
                "/status — bot status\n"
                "/portfolio — open paper positions\n"
                "/trades — recent closed trades\n"
                "/help — commands"
            ))
        elif command == "/status":
            self._reply(chat_id, self._status())
        elif command == "/portfolio":
            self._reply(chat_id, self._portfolio())
        elif command == "/trades":
            self._reply(chat_id, self._trades())
        else:
            self._reply(chat_id, "Unknown command. Send /help to see available commands.")

    def _poll(self) -> None:
        # Discard commands sent while the service was offline; the user can send /start again.
        initial = _call(self.token, "getUpdates", {"offset": -1, "timeout": 0, "allowed_updates": ["message"]}, timeout=10)
        offset = None
        if initial and initial.get("result"):
            offset = initial["result"][-1]["update_id"] + 1

        while not self._stop.is_set():
            payload = {"timeout": 20, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset
            data = _call(self.token, "getUpdates", payload, timeout=25)
            if not data:
                time.sleep(2)
                continue
            for update in data.get("result", []):
                offset = int(update["update_id"]) + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                chat_id = str(chat.get("id", ""))
                text = message.get("text", "")
                if chat_id and text:
                    self._handle(chat_id, text)
