import logging
from typing import Optional
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)
IST_TIMEZONE = "Asia/Kolkata"

def filter_nse_regular_session(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    result = df.copy()
    if not isinstance(result.index, pd.DatetimeIndex):
        raise ValueError("Market data must have a DatetimeIndex.")
    if result.index.tz is None:
        result.index = result.index.tz_localize(IST_TIMEZONE)
    else:
        result.index = result.index.tz_convert(IST_TIMEZONE)
    return result.between_time("09:15", "15:30", inclusive="both").sort_index()

class NSEDataProvider:
    def __init__(self, timeout: int = 10):
        self.timeout = int(timeout)

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Symbol cannot be empty.")
        return symbol if symbol.endswith(".NS") else f"{symbol}.NS"

    def get_ohlcv(self, symbol: str, interval: str = "15m", period: str = "1d") -> pd.DataFrame:
        formatted = self._format_symbol(symbol)
        try:
            df = yf.Ticker(formatted).history(period=period, interval=interval, prepost=False,
                auto_adjust=False, repair=True, timeout=self.timeout)
            if df is None or df.empty:
                return pd.DataFrame()
            cols = ["Open","High","Low","Close","Volume"]
            if set(cols) - set(df.columns):
                return pd.DataFrame()
            df = df[cols].copy()
            df = df[~df.index.duplicated(keep="last")]
            for c in cols:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=cols)
            return filter_nse_regular_session(df)
        except Exception as exc:
            logger.exception("Failed to fetch %s: %s", formatted, exc)
            return pd.DataFrame()

    def get_india_vix(self) -> Optional[float]:
        try:
            df = yf.Ticker("^INDIAVIX").history(period="1d", interval="1m", prepost=False,
                auto_adjust=False, timeout=self.timeout)
            if df is None or df.empty or "Close" not in df.columns:
                return None
            close = pd.to_numeric(df["Close"], errors="coerce").dropna()
            return float(close.iloc[-1]) if not close.empty and float(close.iloc[-1]) > 0 else None
        except Exception as exc:
            logger.exception("Failed to fetch India VIX: %s", exc)
            return None

    def get_nifty_daily(self, period: str = "6mo") -> pd.DataFrame:
        try:
            df = yf.Ticker("^NSEI").history(period=period, interval="1d", prepost=False,
                auto_adjust=False, timeout=self.timeout)
            return df.sort_index() if df is not None and not df.empty else pd.DataFrame()
        except Exception as exc:
            logger.exception("Failed to fetch Nifty data: %s", exc)
            return pd.DataFrame()
