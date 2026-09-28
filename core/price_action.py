def bullish_hammer(c):
 body=abs(c.close-c.open); lower=min(c.open,c.close)-c.low; upper=c.high-max(c.open,c.close)
 return lower>=2*max(body,1e-9) and upper<=body and c.close>c.open
def bullish_engulfing(df):
 if len(df)<2:return False
 a,b=df.iloc[-2],df.iloc[-1]; return a.close<a.open and b.close>b.open and b.open<=a.close and b.close>=a.open
def breakout_with_volume(df,lookback=20,mult=2):
 if len(df)<lookback+1:return False
 x=df.iloc[-1]; return x.close>df.high.iloc[-lookback-1:-1].max() and x.volume>=mult*df.volume.iloc[-lookback-1:-1].mean()
def timeframe_signal(df):
 return {"hammer":False if df.empty else bullish_hammer(df.iloc[-1]),"engulfing":bullish_engulfing(df),"breakout":breakout_with_volume(df)}
def multi_timeframe_confirmation(d,m15,m5):
 s={"1D":timeframe_signal(d),"15m":timeframe_signal(m15),"5m":timeframe_signal(m5)}
 return sum(any(v.values()) for v in s.values())>=2,s