from dataclasses import dataclass
@dataclass(frozen=True)
class MacroDecision: allowed:bool; reason:str
def check_macro(nifty_daily,vix,vix_max=22):
 if nifty_daily.empty or "close" not in nifty_daily or len(nifty_daily)<20:return MacroDecision(False,"Insufficient Nifty data")
 c=nifty_daily.close.astype(float); ema=c.ewm(span=20,adjust=False).mean().iloc[-1]; trend=c.iloc[-1]>ema; ok=trend and float(vix)<vix_max
 return MacroDecision(ok,f"Nifty>EMA20={trend}, VIX={float(vix):.2f}")