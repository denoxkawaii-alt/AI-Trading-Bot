from config.settings import SETTINGS
from core.macro_filter import check_macro
from core.order_flow import detect_liquidity_sweep,analyze_order_book
from core.price_action import multi_timeframe_confirmation
from core.quant_engine import build_long_plan
from execution.paper_trader import PaperTrader
from execution.telegram_notifier import trade_alert
from data_provider import CsvDemoProvider
def run_once(symbols,provider=None,trader=None):
 provider=provider or CsvDemoProvider(); trader=trader or PaperTrader(SETTINGS.DEMO_CAPITAL)
 m=check_macro(provider.get_nifty_daily(),provider.get_vix(),SETTINGS.VIX_MAX)
 if not m.allowed:return {"status":"BLOCKED","reason":m.reason}
 n=0
 for symbol in symbols:
  if n>=SETTINGS.MAX_TRADES_PER_DAY or symbol in trader.positions:break
  d,m15,m5=[provider.get_ohlcv(symbol,x) for x in ("1D","15m","5m")]
  ok,_=multi_timeframe_confirmation(d,m15,m5)
  if not ok:continue
  a,b=m5.iloc[-1],m5.iloc[-2]
  if detect_liquidity_sweep(b.high,b.low,a.high,a.low,a.close):continue
  bid,ask=provider.get_order_book(symbol)
  if not analyze_order_book(bid,ask).bullish:continue
  p=build_long_plan(m5,trader.equity,SETTINGS.MAX_RISK_PER_TRADE,SETTINGS.MIN_RR,SETTINGS.MIN_MC_PROBABILITY,SETTINGS.MONTE_CARLO_RUNS)
  if p and trader.open_position(symbol,p):trade_alert(symbol,p);n+=1
 return {"status":"OK","equity":trader.equity,"positions":list(trader.positions)}
if __name__=="__main__":print(run_once([]))