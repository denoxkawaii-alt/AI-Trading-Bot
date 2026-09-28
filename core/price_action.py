# core/price_action.py

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ORBSignal:
    """Result produced by the 15-minute ORB strategy."""

    signal: str
    entry: Optional[float]
    stop_loss: Optional[float]
    target: Optional[float]
    risk_per_share: Optional[float]
    reward_per_share: Optional[float]
    risk_reward: Optional[float]
    opening_range_high: Optional[float]
    opening_range_low: Optional[float]
    average_volume: Optional[float]
    latest_volume: Optional[float]
    reason: str


class PriceActionEngine:
    """
    Layer 3: 15-minute Opening Range Breakout + Volume Spike.

    Rules:
      - First 15-minute candle defines the opening range.
      - Latest close must be above opening-range high.
      - Latest volume must be > 1.5x average volume of the
        previous 10 candles (excluding the breakout candle).
      - Stop loss = breakout candle low; opening-range low is
        used as a defensive fallback.
      - Target = minimum 1:1.5 risk/reward.
    """

    DEFAULT_VOLUME_LOOKBACK = 10
    DEFAULT_VOLUME_MULTIPLIER = 1.5
    DEFAULT_MIN_RR = 1.5

    def __init__(
        self,
        volume_lookback: int = DEFAULT_VOLUME_LOOKBACK,
        volume_multiplier: float = DEFAULT_VOLUME_MULTIPLIER,
        min_risk_reward: float = DEFAULT_MIN_RR,
    ):
        if volume_lookback <= 0:
            raise ValueError("volume_lookback must be greater than 0")
        if volume_multiplier <= 0:
            raise ValueError("volume_multiplier must be greater than 0")
        if min_risk_reward <= 0:
            raise ValueError("min_risk_reward must be greater than 0")

        self.volume_lookback = int(volume_lookback)
        self.volume_multiplier = float(volume_multiplier)
        self.min_risk_reward = float(min_risk_reward)

    def generate_signal(self, df: pd.DataFrame) -> ORBSignal:
        """Evaluate the latest 15-minute candle for an ORB breakout."""
        try:
            self._validate_dataframe(df)
            data = self._prepare_data(df)

            if len(data) < self.volume_lookback + 1:
                return self._no_signal(
                    "Insufficient candles for volume calculation."
                )

            opening_range = self._get_opening_range(data)
            if opening_range is None:
                return self._no_signal(
                    "15-minute opening range could not be identified."
                )

            opening_high, opening_low = opening_range
            latest = data.iloc[-1]

            latest_close = float(latest["Close"])
            latest_low = float(latest["Low"])
            latest_volume = float(latest["Volume"])

            previous_volumes = data["Volume"].iloc[
                -self.volume_lookback - 1:-1
            ]
            if len(previous_volumes) < self.volume_lookback:
                return self._no_signal(
                    "Insufficient historical volume candles."
                )

            average_volume = float(previous_volumes.mean())
            if average_volume <= 0:
                return self._no_signal(
                    "Average volume is zero or invalid."
                )

            volume_threshold = (
                average_volume * self.volume_multiplier
            )

            if latest_close <= opening_high:
                return self._no_signal(
                    f"No ORB breakout: Close={latest_close:.2f}, "
                    f"OpeningHigh={opening_high:.2f}."
                )

            if latest_volume <= volume_threshold:
                return self._no_signal(
                    f"Volume spike missing: Volume={latest_volume:.0f}, "
                    f"Required>{volume_threshold:.0f}."
                )

            entry = latest_close
            stop_loss = latest_low

            # Defensive fallback requested by the strategy specification.
            if stop_loss >= entry:
                stop_loss = opening_low

            if stop_loss >= entry:
                return self._no_signal(
                    "Invalid risk structure: Stop Loss is not below entry."
                )

            risk_per_share = entry - stop_loss
            if risk_per_share <= 0:
                return self._no_signal(
                    "Risk per share must be positive."
                )

            reward_per_share = (
                risk_per_share * self.min_risk_reward
            )
            target = entry + reward_per_share
            risk_reward = reward_per_share / risk_per_share

            if risk_reward < self.min_risk_reward:
                return self._no_signal(
                    "Calculated Risk/Reward is below minimum."
                )

            reason = (
                f"ORB BREAKOUT confirmed: Close={entry:.2f} > "
                f"OpeningHigh={opening_high:.2f}; "
                f"Volume={latest_volume:.0f} > "
                f"{volume_threshold:.0f}; RR=1:{risk_reward:.2f}."
            )
            logger.info("Price Action: %s", reason)

            return ORBSignal(
                signal="BUY",
                entry=entry,
                stop_loss=stop_loss,
                target=target,
                risk_per_share=risk_per_share,
                reward_per_share=reward_per_share,
                risk_reward=risk_reward,
                opening_range_high=opening_high,
                opening_range_low=opening_low,
                average_volume=average_volume,
                latest_volume=latest_volume,
                reason=reason,
            )

        except Exception as exc:
            logger.exception("Price Action Engine failed: %s", exc)
            return self._no_signal(
                f"Price Action evaluation failed: {exc}"
            )

    @staticmethod
    def _get_opening_range(
        df: pd.DataFrame,
    ) -> Optional[tuple[float, float]]:
        """
        Return the first candle's high/low.

        The caller must supply data restricted to the regular NSE
        session and beginning at the 09:15 opening candle. This
        prevents multi-day data from treating an old candle as today's ORB.
        """
        if df.empty:
            return None

        first_candle = df.iloc[0]
        opening_high = float(first_candle["High"])
        opening_low = float(first_candle["Low"])

        if opening_high <= 0 or opening_low <= 0:
            return None
        if opening_high < opening_low:
            return None

        return opening_high, opening_low

    @staticmethod
    def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate OHLCV data before analysis."""
        data = df.copy().sort_index()
        data = data[~data.index.duplicated(keep="last")]

        numeric_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        for column in numeric_columns:
            data[column] = pd.to_numeric(
                data[column], errors="coerce"
            )

        data = data.dropna(subset=numeric_columns)

        data = data[
            (data["High"] >= data["Low"])
            & (data["High"] >= data["Open"])
            & (data["High"] >= data["Close"])
            & (data["Low"] <= data["Open"])
            & (data["Low"] <= data["Close"])
            & (data["Volume"] >= 0)
        ]

        return data

    @staticmethod
    def _validate_dataframe(df: pd.DataFrame) -> None:
        """Validate required market-data structure."""
        if df is None or df.empty:
            raise ValueError(
                "Price Action Engine received empty market data."
            )

        required_columns = {
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        }
        missing = required_columns.difference(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

    @staticmethod
    def _no_signal(reason: str) -> ORBSignal:
        """Return a standardized NO_TRADE result."""
        logger.info("Price Action: NO TRADE - %s", reason)

        return ORBSignal(
            signal="NO_TRADE",
            entry=None,
            stop_loss=None,
            target=None,
            risk_per_share=None,
            reward_per_share=None,
            risk_reward=None,
            opening_range_high=None,
            opening_range_low=None,
            average_volume=None,
            latest_volume=None,
            reason=reason,
        )
