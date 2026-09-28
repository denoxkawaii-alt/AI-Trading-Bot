import logging
from typing import Tuple
import pandas as pd

logger = logging.getLogger(__name__)

class TrendEngine:
    """Layer 2: Nifty EMA20/EMA50 trend engine."""
    FAST_EMA = 20
    SLOW_EMA = 50

    def __init__(self, fast_period=FAST_EMA, slow_period=SLOW_EMA):
        if fast_period <= 0 or slow_period <= 0:
            raise ValueError("EMA periods must be greater than 0")
        if fast_period >= slow_period:
            raise ValueError("fast_period must be smaller than slow_period")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def calculate_emas(self, df):
        self._validate_dataframe(df)
        result = df.copy()
        result["EMA20"] = result["Close"].ewm(span=self.fast_period, adjust=False, min_periods=self.fast_period).mean()
        result["EMA50"] = result["Close"].ewm(span=self.slow_period, adjust=False, min_periods=self.slow_period).mean()
        return result

    def get_trend(self, df) -> Tuple[str, str]:
        result = self.calculate_emas(df)
        valid = result.dropna(subset=["Close", "EMA20", "EMA50"])
        if valid.empty:
            return "NEUTRAL", "Insufficient data for EMA calculation."
        latest = valid.iloc[-1]
        close, ema20, ema50 = float(latest["Close"]), float(latest["EMA20"]), float(latest["EMA50"])
        if close > ema50 and ema20 > ema50:
            return "BULLISH", f"BULLISH: Close={close:.2f} > EMA50={ema50:.2f}, EMA20={ema20:.2f} > EMA50."
        if close < ema50 and ema20 < ema50:
            return "BEARISH", f"BEARISH: Close={close:.2f} < EMA50={ema50:.2f}, EMA20={ema20:.2f} < EMA50."
        return "NEUTRAL", f"NEUTRAL: Close={close:.2f}, EMA20={ema20:.2f}, EMA50={ema50:.2f}."

    @staticmethod
    def _validate_dataframe(df):
        if df is None or df.empty:
            raise ValueError("Trend Engine received empty market data.")
        if "Close" not in df.columns:
            raise ValueError("Market data must contain a 'Close' column.")
        if df["Close"].dropna().empty:
            raise ValueError("Close column contains no valid values.")
