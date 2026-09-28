from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class TradePlan:
    side:str; entry:float; stop:float; target:float; quantity:int
    risk_rupees:float; rr:float; mc_probability:float

def atr(df,period=14):
    pc=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])

def monte_carlo_probability(returns,entry,stop,target,runs=1000,horizon=30,seed=42):
    r=pd.Series(returns).dropna().astype(float).to_numpy()
    if len(r)<20:return 0.0
    rng=np.random.default_rng(seed)
    samples=rng.choice(r,size=(runs,horizon),replace=True)
    paths=entry*np.exp(np.cumsum(samples,axis=1))
    success=(paths.max(axis=1)>=target)&(paths.min(axis=1)>stop)
    return float(success.mean())

def build_long_plan(df,capital=10000,max_risk=150,min_rr=2.5,mc_threshold=.85,runs=1000):
    entry=float(df.close.iloc[-1]); a=atr(df)
    if not np.isfinite(a) or a<=0:return None
    stop=entry-1.5*a; target=entry+3.75*a
    risk_per_share=entry-stop
    qty=min(int(max_risk//risk_per_share),int(capital//entry))
    if qty<1:return None
    rr=(target-entry)/risk_per_share
    if rr<min_rr:return None
    p=monte_carlo_probability(df.close.pct_change(),entry,stop,target,runs)
    return None if p<mc_threshold else TradePlan("BUY",entry,stop,target,qty,qty*risk_per_share,rr,p)
