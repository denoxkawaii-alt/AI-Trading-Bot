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
    """Dependency-free Telegram command poller for the paper-trading worker."""

    def __init__(self, trader, data_dir: str):
        self.trader = trader
        self.data_dir = Path(data_dir)
        self.token = SETTINGS.TELEGRAM_BOT_TOKEN.strip()
        self.allowed_chat_id = SETTINGS.TELEGRAM_CHAT_ID.strip()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        # TELEGRAM_CHAT_ID is deliberately optional: when missing/wrong, the bot can
        # reply with the actual incoming chat ID so configuration can be repaired.
        if not self.token:
            logger.error("Telegram command bot disabled: TELEGRAM_BOT_TOKEN is missing.")
            return

        me = _call(self.token, "getMe", {}, timeout=15)
        if not me:
            logger.error("Telegram bot authentication failed. Check TELEGRAM_BOT_TOKEN in Railway.")
            return

        username = (me.get("result") or {}).get("username", "(unknown)")
        logger.info("Telegram bot authenticated as @%s.", username)

        # Polling and a Telegram webhook cannot be active at the same time.
        webhook = _call(self.token, "deleteWebhook", {"drop_pending_updates": False}, timeout=15)
        if webhook is None:
            logger.warning("Telegram webhook cleanup failed; polling will keep retrying.")

        self._thread = threading.Thread(target=self._poll, name="telegram-command-bot", daemon=True)
        self._thread.start()
        logger.info(
            "Telegram command bot started. Configured chat ID: %s",
            self.allowed_chat_id or "(not configured; diagnostic mode)",
        )

    def stop(self) -> None:
        self._stop.set()

    def _reply(self, chat_id: str, message: str) -> None:
        if not send_message(self.token, chat_id, message):
            logger.error("Telegram reply failed for chat %s.", chat_id)

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
        if self.allowed_chat_id and str(chat_id) != self.allowed_chat_id:
            logger.warning(
                "Ignoring Telegram command from unauthorized chat %s (configured chat id: %s).",
                chat_id,
                self.allowed_chat_id,
            )
            send_message(
                self.token,
                chat_id,
                "⚠️ Telegram bot is running, but this chat is not authorized.\n\n"
                f"Chat ID: {chat_id}\n"
                f"Configured chat ID: {self.allowed_chat_id}\n\n"
                "Update TELEGRAM_CHAT_ID in Railway to this Chat ID, then redeploy.",
            )
            return

        # If no TELEGRAM_CHAT_ID is configured, allow the first chat through so the
        # owner can confirm connectivity and then lock the bot to that chat.
        if not self.allowed_chat_id:
            logger.warning("Telegram chat ID is not configured; accepting diagnostic chat %s.", chat_id)
            self._reply(
                chat_id,
                "⚠️ TELEGRAM_CHAT_ID is not configured in Railway.\n\n"
                f"Your Chat ID is: {chat_id}\n\n"
                "Set this value as TELEGRAM_CHAT_ID and redeploy to lock the bot to your chat.",
            )
            return

        command = (text or "").strip().split()[0].lower() if text else ""
        if "@" in command:
            command = command.split("@", 1)[0]

        if command in {"/start", "/help"}:
            self._reply(
                chat_id,
                "🤖 Kakashi AI Trading Bot\n\n"
                "Bot is connected and running in PAPER mode.\n\n"
                "/status — bot status\n"
                "/portfolio — open paper positions\n"
                "/trades — recent closed trades\n"
                "/help — commands",
            )
        elif command == "/status":
            self._reply(chat_id, self._status())
        elif command == "/portfolio":
            self._reply(chat_id, self._portfolio())
        elif command == "/trades":
            self._reply(chat_id, self._trades())
        else:
            self._reply(chat_id, "Unknown command. Send /help to see available commands.")

    def _poll(self) -> None:
        offset = None
        while not self._stop.is_set():
            # Retry webhook cleanup periodically so a stale webhook cannot permanently
            # block getUpdates after a redeploy.
            _call(self.token, "deleteWebhook", {"drop_pending_updates": False}, timeout=15)

            payload = {"timeout": 20, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset

            data = _call(self.token, "getUpdates", payload, timeout=25)
            if not data:
                time.sleep(3)
                continue

            for update in data.get("result", []):
                offset = int(update["update_id"]) + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                chat_id = str(chat.get("id", ""))
                text = message.get("text", "")
                if chat_id and text:
                    try:
                        self._handle(chat_id, text)
                    except Exception:
                        logger.exception("Telegram command handling failed for chat %s.", chat_id)
