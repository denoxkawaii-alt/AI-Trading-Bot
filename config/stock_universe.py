import io
import logging
from typing import Iterable

import pandas as pd
import requests
import yfinance as yf

from config.settings import SETTINGS

logger = logging.getLogger(__name__)
NSE_EQUITY_CSV = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
FALLBACK_NIFTY_50 = ["ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE",
"BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL","GRASIM","HCLTECH",
"HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR","ICICIBANK","INDUSINDBK","INFY","ITC","JIOFIN",
"JSWSTEEL","KOTAKBANK","LT","M&M","MARUTI","MAXHEALTH","NESTLEIND","NTPC","ONGC","POWERGRID","RELIANCE",
"SBILIFE","SBIN","SHRIRAMFIN","SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS","TECHM","TITAN",
"TRENT","ULTRACEMCO","WIPRO"]


def _download_nse_symbols(url: str = NSE_EQUITY_CSV) -> list[str]:
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*"})
    response.raise_for_status()
    frame = pd.read_csv(io.BytesIO(response.content))
    frame.columns = [str(c).strip().upper() for c in frame.columns]
    if "SYMBOL" not in frame.columns:
        raise ValueError("NSE universe response has no SYMBOL column.")
    if "SERIES" in frame.columns:
        frame = frame[frame["SERIES"].astype(str).str.upper().eq("EQ")]
    symbols = frame["SYMBOL"].astype(str).str.strip().str.upper().dropna().drop_duplicates().tolist()
    if not symbols:
        raise ValueError("NSE universe returned no equity symbols.")
    return symbols


def _quote_filter(symbols: Iterable[str], min_price: float, min_daily_volume: int, chunk_size: int = 100) -> list[str]:
    candidates = list(symbols)
    selected: list[str] = []
    for start in range(0, len(candidates), chunk_size):
        chunk = candidates[start:start + chunk_size]
        try:
            data = yf.download(tickers=[f"{s}.NS" for s in chunk], period="5d", interval="1d",
                               auto_adjust=False, progress=False, group_by="ticker", threads=True)
        except Exception as exc:
            logger.warning("Quote batch failed for symbols %d-%d: %s", start, start + len(chunk), exc)
            continue
        if data is None or data.empty:
            continue
        for symbol in chunk:
            ticker = f"{symbol}.NS"
            try:
                quote = data[ticker] if isinstance(data.columns, pd.MultiIndex) else data
                close = pd.to_numeric(quote["Close"], errors="coerce").dropna()
                volume = pd.to_numeric(quote["Volume"], errors="coerce").dropna()
                if not close.empty and not volume.empty and float(close.iloc[-1]) >= min_price and float(volume.tail(5).mean()) >= min_daily_volume:
                    selected.append(symbol)
            except (KeyError, TypeError, ValueError):
                continue
    return selected


def fetch_nse_universe(url: str = NSE_EQUITY_CSV, min_price: float | None = None,
                       min_daily_volume: int | None = None) -> list[str]:
    """Fetch current NSE EQ symbols and exclude penny/illiquid stocks; fall back to Nifty 50 on failure."""
    min_price = SETTINGS.MIN_PRICE if min_price is None else float(min_price)
    min_daily_volume = SETTINGS.MIN_DAILY_VOLUME if min_daily_volume is None else int(min_daily_volume)
    try:
        symbols = _download_nse_symbols(url)
        filtered = _quote_filter(symbols, min_price, min_daily_volume)
        if filtered:
            logger.info("Dynamic NSE universe: %d liquid symbols from %d EQ symbols.", len(filtered), len(symbols))
            return filtered
        raise RuntimeError("Quote filter returned no eligible symbols.")
    except Exception as exc:
        logger.warning("Dynamic NSE universe failed: %s. Using Nifty 50 fallback.", exc)
        return FALLBACK_NIFTY_50.copy()


def filter_liquid_stocks(universe: pd.DataFrame, quotes: pd.DataFrame) -> pd.DataFrame:
    req = {"SYMBOL", "LAST_PRICE", "AVG_VOLUME"}
    missing = req - set(quotes.columns)
    if missing:
        raise ValueError(f"Missing quote columns: {sorted(missing)}")
    x = universe.merge(quotes, on="SYMBOL", how="inner")
    return x[(x.LAST_PRICE >= SETTINGS.MIN_PRICE) & (x.AVG_VOLUME >= SETTINGS.MIN_DAILY_VOLUME)].copy()
