import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class MacroFilter:
    """Layer 1: India VIX + Nifty trend safety filter."""
    VALID_TRENDS = {"BULLISH", "NEUTRAL", "BEARISH"}

    def __init__(self, max_vix_threshold=22.0, allow_neutral=False):
        if max_vix_threshold <= 0:
            raise ValueError("max_vix_threshold must be greater than 0")
        self.max_vix_threshold = float(max_vix_threshold)
        self.allow_neutral = allow_neutral

    def evaluate_macro_safety(self, vix_value: Optional[float], index_trend: str) -> Tuple[bool, str]:
        if vix_value is None: return False, "India VIX data unavailable."
        if vix_value <= 0: return False, "Invalid India VIX value."
        if vix_value > self.max_vix_threshold: return False, f"India VIX too high ({vix_value:.2f})."
        trend = str(index_trend).strip().upper()
        if trend not in self.VALID_TRENDS: return False, "Nifty trend unavailable or invalid."
        if trend == "BEARISH": return False, "Main Market Index (Nifty) is Bearish."
        if trend == "NEUTRAL" and not self.allow_neutral: return False, "Main Market Index (Nifty) is Neutral (Strict Mode)."
        return True, f"Macro conditions safe (VIX={vix_value:.2f}, Trend={trend})."
