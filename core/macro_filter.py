from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class MacroDecision:
    allowed: bool
    reason: str

def check_macro(nifty_daily: pd.DataFrame,vix: float,vix_max: float=22):
    if nifty_daily.empty or "close" not in nifty_daily or len(nifty_daily)<20:
        return MacroDecision(False,"Insufficient Nifty data")
    close=nifty_daily["close"].astype(float)
    ema=close.ewm(span=20,adjust=False).mean().iloc[-1]
    ok=close.iloc[-1]>ema and float(vix)<vix_max
    return MacroDecision(ok,f"Nifty>EMA20={close.iloc[-1]>ema}, VIX={float(vix):.2f}")
