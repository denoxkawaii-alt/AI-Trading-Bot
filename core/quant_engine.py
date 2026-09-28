from dataclasses import dataclass
import numpy as np,pandas as pd
@dataclass(frozen=True)
class TradePlan:
 side:str; entry:float; stop:float; target:float; quantity:int; risk_rupees:float; rr:float; mc_probability:float
def atr(df,period=14):
 pc=df.close.shift(1); tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1); return float(tr.rolling(period).mean().iloc[-1])
def monte_carlo_probability(returns,entry,stop,target,runs=1000,horizon=30,seed=42):
 r=pd.Series(returns).dropna().astype(float).to_numpy()
 if len(r)<20:return 0.0
 paths=entry*np.exp(np.cumsum(np.random.default_rng(seed).choice(r,(runs,horizon),replace=True),axis=1))
 return float(((paths.max(1)>=target)&(paths.min(1)>stop)).mean())
def build_long_plan(df,capital=10000,max_risk=150,min_rr=2.5,mc_threshold=.85,runs=1000):
 e=float(df.close.iloc[-1]); a=atr(df)
 if not np.isfinite(a) or a<=0:return None
 s=e-1.5*a; t=e+3.75*a; r=e-s; q=min(int(max_risk//r),int(capital//e))
 if q<1 or (t-e)/r<min_rr:return None
 p=monte_carlo_probability(df.close.pct_change(),e,s,t,runs)
 return None if p<mc_threshold else TradePlan("BUY",e,s,t,q,q*r,(t-e)/r,p)