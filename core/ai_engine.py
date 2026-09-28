"""Lightweight AI-style ensemble gate for paper trading.

This module deliberately has no broker access. It combines independent
market features into a confidence score. It is a fallback until an external
LLM/ML provider is configured; it must never place live orders.
"""
from dataclasses import dataclass
import math
import pandas as pd

@dataclass(frozen=True)
class AIDecision:
    signal: str
    confidence: float
    reason: str

class AITradingEngine:
    def __init__(self, min_confidence: float = 0.65):
        if not 0 < float(min_confidence) <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        self.min_confidence = float(min_confidence)

    def evaluate_buy(self, df: pd.DataFrame, vwap: float | None = None) -> AIDecision:
        if df is None or len(df) < 20:
            return AIDecision("HOLD", 0.0, "Insufficient data for AI ensemble.")
        x = df.copy()
        close = pd.to_numeric(x["Close"], errors="coerce").dropna()
        if len(close) < 20:
            return AIDecision("HOLD", 0.0, "Insufficient valid close data.")
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        latest = float(close.iloc[-1])
        returns = close.pct_change().dropna()
        momentum = float(returns.tail(5).mean())
        volatility = float(returns.tail(20).std())
        score = 0.50
        reasons = []
        if latest > ema20 > ema50:
            score += 0.20; reasons.append("EMA alignment bullish")
        elif latest < ema20:
            score -= 0.15; reasons.append("price below EMA20")
        if momentum > 0:
            score += min(0.15, momentum * 100)
            reasons.append("short-term momentum positive")
        else:
            score -= min(0.10, abs(momentum) * 100)
        if vwap is not None and math.isfinite(float(vwap)):
            if latest >= float(vwap):
                score += 0.10; reasons.append("price above VWAP")
            else:
                score -= 0.10; reasons.append("price below VWAP")
        if volatility > 0.03:
            score -= 0.05; reasons.append("high short-term volatility")
        confidence = max(0.0, min(1.0, score))
        signal = "BUY" if confidence >= self.min_confidence else "HOLD"
        return AIDecision(signal, confidence, "; ".join(reasons) or "neutral feature set")
