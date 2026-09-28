import logging
from typing import Optional
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

class NSEDataProvider:
    """Yahoo Finance NSE provider for paper trading/research."""
    def __init__(self, timeout=10): self.timeout = timeout

    @staticmethod
    def _format_symbol(symbol):
        symbol = symbol.strip().upper()
        return symbol if symbol.endswith(".NS") else f"{symbol}.NS"

    def get_ohlcv(self, symbol, interval="15m", period="5d"):
        formatted = self._format_symbol(symbol)
        try:
            df = yf.Ticker(formatted).history(period=period, interval=interval, prepost=False, auto_adjust=False, repair=True, timeout=self.timeout)
            if df is None or df.empty: return pd.DataFrame()
            cols=["Open","High","Low","Close","Volume"]
            if any(c not in df.columns for c in cols): return pd.DataFrame()
            df=df[cols].copy()
            df=df[~df.index.duplicated(keep="last")].dropna(subset=["Open","High","Low","Close"])
            return df.sort_index()
        except Exception as exc:
            logger.exception("Failed to fetch %s: %s", formatted, exc)
            return pd.DataFrame()

    def get_india_vix(self) -> Optional[float]:
        try:
            df=yf.Ticker("^INDIAVIX").history(period="1d",interval="1m",prepost=False,auto_adjust=False,timeout=self.timeout)
            if df is None or df.empty or "Close" not in df.columns: return None
            close=df["Close"].dropna()
            if close.empty: return None
            value=float(close.iloc[-1])
            return value if value>0 else None
        except Exception as exc:
            logger.exception("Failed to fetch India VIX: %s", exc)
            return None

    def get_nifty_daily(self, period="6mo"):
        try:
            df=yf.Ticker("^NSEI").history(period=period,interval="1d",prepost=False,auto_adjust=False,timeout=self.timeout)
            return df.sort_index() if df is not None and not df.empty else pd.DataFrame()
        except Exception as exc:
            logger.exception("Failed to fetch Nifty data: %s", exc)
            return pd.DataFrame()
