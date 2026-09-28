from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class TradePlan:
    side: str
    entry: float
    stop: float
    target: float
    quantity: int
    risk_rupees: float
    rr: float
    mc_probability: float

def _series(df, name):
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    lower = {str(c).lower(): c for c in df.columns}
    if name.lower() in lower:
        return pd.to_numeric(df[lower[name.lower()]], errors="coerce")
    raise ValueError(f"Missing column: {name}")

def atr(df, period=14):
    high, low, close = _series(df,"High"), _series(df,"Low"), _series(df,"Close")
    pc = close.shift(1)
    tr = pd.concat([high-low,(high-pc).abs(),(low-pc).abs()],axis=1).max(axis=1)
    value = tr.rolling(period,min_periods=period).mean().iloc[-1]
    return float(value)

def monte_carlo_probability(returns, entry, stop, target, runs=1000, horizon=30, seed=42):
    r=pd.Series(returns).dropna().astype(float).to_numpy()
    r=r[np.isfinite(r)]
    if len(r)<20: return 0.0
    paths=entry*np.exp(np.cumsum(np.random.default_rng(seed).choice(r,(runs,horizon),replace=True),axis=1))
    return float(np.mean((paths.max(axis=1)>=target)&(paths.min(axis=1)>stop)))

def build_long_plan(df, capital=10000, max_risk=150, min_rr=2.5, mc_threshold=0.85, runs=1000):
    close=_series(df,"Close")
    entry=float(close.iloc[-1])
    a=atr(df)
    if not np.isfinite(a) or a<=0: return None
    stop=entry-1.5*a
    target=entry+3.75*a
    risk=entry-stop
    quantity=min(int(max_risk//risk),int(capital//entry))
    if quantity<1: return None
    rr=(target-entry)/risk
    if rr<min_rr: return None
    probability=monte_carlo_probability(close.pct_change(),entry,stop,target,runs=runs)
    if probability<mc_threshold: return None
    return TradePlan("BUY",entry,stop,target,quantity,quantity*risk,rr,probability)
