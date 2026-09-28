"""NSE universe discovery/filtering. Use a licensed market-data source in production."""
import io
import pandas as pd
import requests
from config.settings import SETTINGS

NSE_EQUITY_CSV="https://archives.nseindia.com/content/equities/EQUITY_L.csv"

def fetch_nse_universe(url=NSE_EQUITY_CSV):
    r=requests.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    df=pd.read_csv(io.BytesIO(r.content))
    df.columns=[c.strip().upper() for c in df.columns]
    return df

def filter_liquid_stocks(universe,quotes):
    required={"SYMBOL","LAST_PRICE","AVG_VOLUME"}
    missing=required-set(quotes.columns)
    if missing: raise ValueError(f"Missing quote columns: {sorted(missing)}")
    x=universe.merge(quotes,on="SYMBOL",how="inner")
    return x[(x.LAST_PRICE>=SETTINGS.MIN_PRICE)&(x.AVG_VOLUME>=SETTINGS.MIN_DAILY_VOLUME)].copy()
