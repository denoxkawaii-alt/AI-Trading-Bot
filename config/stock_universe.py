import io,pandas as pd,requests
from config.settings import SETTINGS
NSE_EQUITY_CSV="https://archives.nseindia.com/content/equities/EQUITY_L.csv"
def fetch_nse_universe(url=NSE_EQUITY_CSV):
 r=requests.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0"}); r.raise_for_status()
 x=pd.read_csv(io.BytesIO(r.content)); x.columns=[c.strip().upper() for c in x.columns]; return x
def filter_liquid_stocks(universe,quotes):
 req={"SYMBOL","LAST_PRICE","AVG_VOLUME"}; miss=req-set(quotes.columns)
 if miss: raise ValueError(f"Missing quote columns: {sorted(miss)}")
 x=universe.merge(quotes,on="SYMBOL",how="inner")
 return x[(x.LAST_PRICE>=SETTINGS.MIN_PRICE)&(x.AVG_VOLUME>=SETTINGS.MIN_DAILY_VOLUME)].copy()