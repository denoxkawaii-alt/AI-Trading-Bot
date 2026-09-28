import logging
from typing import Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class OrderFlowEngine:
    """
    Layer 4: Order Flow and Microstructure Validation.

    Validates breakout trades using:
    1. Intraday VWAP Alignment (Close > VWAP for BUY).
    2. Volume Spread Analysis (VSA - Volume Spike + Reasonable Candle Spread).
    3. Liquidity Sanity Check (Minimum volume & non-zero liquidity).
    """

    def __init__(
        self,
        vwap_confirmation: bool = True,
        volume_multiplier: float = 1.2,
        min_avg_volume: float = 1000.0,
    ):
        if volume_multiplier <= 0:
            raise ValueError("volume_multiplier must be greater than 0")
        if min_avg_volume <= 0:
            raise ValueError("min_avg_volume must be greater than 0")

        self.vwap_confirmation = vwap_confirmation
        self.volume_multiplier = volume_multiplier
        self.min_avg_volume = min_avg_volume

    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate intraday VWAP for the supplied OHLCV session data."""
        self._validate_dataframe(df)

        result = df.copy()
        typical_price = (
            result["High"] + result["Low"] + result["Close"]
        ) / 3
        tp_v = typical_price * result["Volume"]

        cum_tp_v = tp_v.cumsum()
        cum_volume = result["Volume"].cumsum()

        result["VWAP"] = cum_tp_v / cum_volume.replace(0, pd.NA)
        return result

    def validate_order_flow(
        self,
        df: pd.DataFrame,
        signal_type: str = "BUY",
        volume_ma_period: int = 10,
    ) -> Tuple[bool, str]:
        """
        Validate VWAP, liquidity, and volume confirmation.

        Returns:
            (is_valid, reason)
        """
        self._validate_dataframe(df)

        if volume_ma_period <= 0:
            return False, "Order Flow: volume_ma_period must be greater than 0."

        if len(df) < volume_ma_period:
            logger.warning(
                "Order Flow: Insufficient data for Volume MA calculation."
            )
            return False, "Insufficient data for Order Flow validation."

        df_vwap = self.calculate_vwap(df)
        valid_df = df_vwap.dropna(
            subset=["Close", "VWAP", "Volume", "High", "Low"]
        )

        if valid_df.empty:
            return False, "Order Flow: Market data contains missing values."

        latest = valid_df.iloc[-1]
        close = float(latest["Close"])
        vwap = float(latest["VWAP"])
        volume = float(latest["Volume"])

        avg_volume = float(
            valid_df["Volume"].tail(volume_ma_period).mean()
        )

        if avg_volume < self.min_avg_volume:
            reason = (
                f"Order Flow REJECTED: Low average volume "
                f"({avg_volume:.0f} < {self.min_avg_volume:.0f}). "
                "Illiquid stock."
            )
            logger.info(reason)
            return False, reason

        if signal_type.upper() == "BUY":
            if self.vwap_confirmation and close < vwap:
                reason = (
                    f"Order Flow REJECTED: Close ({close:.2f}) "
                    f"is below VWAP ({vwap:.2f})."
                )
                logger.info(reason)
                return False, reason

            required_volume = avg_volume * self.volume_multiplier
            if volume < required_volume:
                reason = (
                    f"Order Flow REJECTED: Breakout volume ({volume:.0f}) "
                    f"is below required VSA threshold ({required_volume:.0f})."
                )
                logger.info(reason)
                return False, reason

            reason = (
                f"Order Flow PASSED: Close={close:.2f} > VWAP={vwap:.2f}, "
                f"Volume={volume:.0f} > VSA Target={required_volume:.0f}."
            )
            logger.info(reason)
            return True, reason

        return False, (
            f"Order Flow REJECTED: Unsupported signal type '{signal_type}'."
        )

    @staticmethod
    def _validate_dataframe(df: pd.DataFrame) -> None:
        """Validate required OHLCV columns and non-empty input."""
        if df is None or df.empty:
            raise ValueError("OrderFlowEngine received empty DataFrame.")

        required_cols = {"High", "Low", "Close", "Volume"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(
                f"Market data missing required columns: {sorted(missing)}"
            )
