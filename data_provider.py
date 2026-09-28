from abc import ABC,abstractmethod
import pandas as pd
class MarketDataProvider(ABC):
 @abstractmethod
 def get_ohlcv(self,symbol,timeframe,limit=250)->pd.DataFrame:...
 @abstractmethod
 def get_vix(self)->float:...
 @abstractmethod
 def get_order_book(self,symbol):...
 @abstractmethod
 def get_nifty_daily(self)->pd.DataFrame:...
class CsvDemoProvider(MarketDataProvider):
 def __init__(self,directory="sample_data"):self.directory=directory
 def get_ohlcv(self,symbol,timeframe,limit=250):return pd.read_csv(f"{self.directory}/{symbol}_{timeframe}.csv").tail(limit)
 def get_vix(self):return 15.0
 def get_order_book(self,symbol):return (100000.,70000.)
 def get_nifty_daily(self):return pd.read_csv(f"{self.directory}/NIFTY_1D.csv")