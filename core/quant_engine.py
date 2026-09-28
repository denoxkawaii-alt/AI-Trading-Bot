import logging
from typing import Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class QuantEngine:
    """Monte Carlo validator. Never overwrites ORB Entry/SL/Target."""
    def __init__(self, default_simulations: int = 1000, default_horizon: int = 10, default_min_probability: float = 0.85):
        if default_simulations < 100 or default_horizon <= 0 or not 0 < default_min_probability <= 1:
            raise ValueError("Invalid Monte Carlo configuration.")
        self.default_simulations = int(default_simulations)
        self.default_horizon = int(default_horizon)
        self.default_min_probability = float(default_min_probability)

    def evaluate_orb_trade_plan(self, entry: float, stop_loss: float, target: float, df: pd.DataFrame,
                                simulations: int | None = None, horizon: int | None = None,
                                min_probability: float | None = None) -> Tuple[bool, float, str]:
        simulations = self.default_simulations if simulations is None else int(simulations)
        horizon = self.default_horizon if horizon is None else int(horizon)
        threshold = self.default_min_probability if min_probability is None else float(min_probability)
        if not (stop_loss < entry < target):
            return False, 0.0, "Invalid ORB levels: expected SL < Entry < Target."
        if simulations < 100 or horizon <= 0 or not 0 < threshold <= 1:
            return False, 0.0, "Invalid Monte Carlo parameters."
        if df is None or df.empty or "Close" not in df.columns:
            return False, 0.0, "Insufficient Close-price data."
        returns = pd.to_numeric(df["Close"], errors="coerce").pct_change()
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns) < 20:
            return False, 0.0, "Insufficient historical returns for Monte Carlo."
        mean_ret, std_ret = float(returns.mean()), float(returns.std())
        if not np.isfinite(std_ret) or std_ret <= 0:
            return False, 0.0, "Return volatility is zero or invalid."
        rng = np.random.default_rng(42)
        simulated = np.clip(rng.normal(mean_ret, std_ret, (simulations, horizon)), -0.999, None)
        paths = entry * np.cumprod(1.0 + simulated, axis=1)
        wins = 0
        for path in paths:
            th = np.flatnonzero(path >= target)
            sh = np.flatnonzero(path <= stop_loss)
            if len(th) and (not len(sh) or th[0] < sh[0]):
                wins += 1
        probability = wins / simulations
        percent = probability * 100.0
        reason = f"Quant MC Win Probability: {percent:.1f}% (required: {threshold*100:.1f}%, simulations={simulations}, horizon={horizon})."
        logger.info(reason)
        return probability >= threshold, percent, reason
