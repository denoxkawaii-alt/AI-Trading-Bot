import logging
from typing import Tuple
import pandas as pd

logger = logging.getLogger(__name__)

class OrderFlowEngine:
    """Layer 4 OHLCV validation: VWAP + VSA volume. Latest breakout candle is excluded from MA."""
    def __init__(self, vwap_confirmation: bool = True, volume_multiplier: float = 1.2,
                 min_avg_volume: float = 1000.0):
        if volume_multiplier <= 0 or min_avg_volume <= 0:
            raise ValueError("Order-flow thresholds must be greater than 0.")
        self.vwap_confirmation = bool(vwap_confirmation)
        self.volume_multiplier = float(volume_multiplier)
        self.min_avg_volume = float(min_avg_volume)

    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        self._validate_dataframe(df)
        result = df.copy()
        tp = (result["High"] + result["Low"] + result["Close"]) / 3.0
        result["VWAP"] = (tp * result["Volume"]).cumsum() / result["Volume"].cumsum().replace(0, pd.NA)
        return result

    def validate_order_flow(self, df: pd.DataFrame, signal_type: str = "BUY",
                            volume_ma_period: int = 10) -> Tuple[bool, str]:
        self._validate_dataframe(df)
        if volume_ma_period <= 0:
            return False, "Invalid volume_ma_period."
        valid = self.calculate_vwap(df).dropna(subset=["Close","VWAP","Volume","High","Low"])
        if len(valid) < volume_ma_period + 1:
            return False, "Insufficient volume history for VSA validation."
        latest = valid.iloc[-1]
        historical_df = valid.iloc[:-1]
        if len(historical_df) < volume_ma_period:
            return False, "Insufficient volume history for VSA validation."
        close, vwap, volume = float(latest["Close"]), float(latest["VWAP"]), float(latest["Volume"])
        avg_volume = float(historical_df["Volume"].tail(volume_ma_period).mean())
        if not pd.notna(avg_volume) or avg_volume <= 0:
            return False, "Invalid historical average volume."
        if avg_volume < self.min_avg_volume:
            return False, f"Order Flow REJECTED: Low average volume ({avg_volume:.0f} < {self.min_avg_volume:.0f})."
        if signal_type.strip().upper() != "BUY":
            return False, f"Unsupported signal type: {signal_type}."
        if self.vwap_confirmation and close < vwap:
            return False, f"Order Flow REJECTED: Close ({close:.2f}) is below VWAP ({vwap:.2f})."
        required = avg_volume * self.volume_multiplier
        if volume < required:
            return False, f"Order Flow REJECTED: Breakout volume ({volume:.0f}) < VSA threshold ({required:.0f})."
        return True, f"Order Flow PASSED: Close={close:.2f}, VWAP={vwap:.2f}, Volume={volume:.0f}, HistoricalAvg={avg_volume:.0f}, Required={required:.0f}."

    @staticmethod
    def _validate_dataframe(df: pd.DataFrame) -> None:
        if df is None or df.empty:
            raise ValueError("OrderFlowEngine received empty DataFrame.")
        missing = {"High","Low","Close","Volume"} - set(df.columns)
        if missing:
            raise ValueError(f"Market data missing required columns: {sorted(missing)}")
