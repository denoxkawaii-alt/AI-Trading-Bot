import logging
from typing import Optional

from config.settings import SETTINGS
from core.macro_filter import MacroFilter
from core.order_flow import OrderFlowEngine
from core.price_action import PriceActionEngine
from core.quant_engine import QuantEngine
from core.trend_engine import TrendEngine
from data_provider import NSEDataProvider
from execution.paper_trader import PaperTrader
from execution.telegram_notifier import trade_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger=logging.getLogger(__name__)

NIFTY_50_STOCKS=["ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR","ICICIBANK","INDUSINDBK","INFY","ITC","JIOFIN","JSWSTEEL","KOTAKBANK","LT","M&M","MARUTI","MAXHEALTH","NESTLEIND","NTPC","ONGC","POWERGRID","RELIANCE","SBILIFE","SBIN","SHRIRAMFIN","SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS","TECHM","TITAN","TRENT","ULTRACEMCO","WIPRO"]

def run_once(symbols:list[str],provider:Optional[NSEDataProvider]=None,trader:Optional[PaperTrader]=None)->dict:
    provider=provider or NSEDataProvider()
    trader=trader or PaperTrader(capital=SETTINGS.DEMO_CAPITAL,max_risk_per_trade=SETTINGS.MAX_RISK_PER_TRADE,
        max_daily_trades=SETTINGS.MAX_TRADES_PER_DAY,cooldown_minutes=SETTINGS.COOLDOWN_MINUTES,min_rr=SETTINGS.MIN_RR)
    result={"status":"STARTING","layer":0,"trades_opened":0,"equity":trader.equity,"positions":list(trader.positions)}
    vix=provider.get_india_vix()
    if vix is None: return {**result,"status":"BLOCKED","layer":1,"reason":"India VIX unavailable. Failing closed."}
    if vix>SETTINGS.VIX_MAX: return {**result,"status":"BLOCKED","layer":1,"reason":f"India VIX too high: {vix:.2f} > {SETTINGS.VIX_MAX:.2f}"}
    nifty=provider.get_nifty_daily()
    if nifty is None or nifty.empty: return {**result,"status":"BLOCKED","layer":2,"reason":"Nifty data unavailable."}
    try: trend,trend_reason=TrendEngine().get_trend(nifty)
    except ValueError as exc: return {**result,"status":"BLOCKED","layer":2,"reason":str(exc)}
    allowed,macro_reason=MacroFilter(SETTINGS.VIX_MAX,allow_neutral=False).evaluate_macro_safety(vix,trend)
    if not allowed: return {**result,"status":"BLOCKED","layer":2,"reason":macro_reason,"trend":trend}
    price=PriceActionEngine(volume_lookback=10,volume_multiplier=1.5,min_risk_reward=SETTINGS.MIN_RR)
    flow=OrderFlowEngine(vwap_confirmation=True,volume_multiplier=1.2,min_avg_volume=1000.0)
    quant=QuantEngine(default_simulations=SETTINGS.MONTE_CARLO_RUNS,default_horizon=SETTINGS.MC_HORIZON,default_min_probability=SETTINGS.MIN_MC_PROBABILITY)
    opened=0
    for raw in symbols:
        symbol=raw.strip().upper()
        if not symbol: continue
        if trader.daily_trade_count>=SETTINGS.MAX_TRADES_PER_DAY: break
        ok,_=trader.can_trade(symbol)
        if not ok: continue
        data=provider.get_ohlcv(symbol,interval="15m",period="1d")
        if data is None or data.empty: continue
        signal=price.generate_signal(data)
        if signal.signal!="BUY": continue
        flow_ok,flow_reason=flow.validate_order_flow(data,"BUY",10)
        if not flow_ok:
            logger.info("%s rejected by Layer 4: %s",symbol,flow_reason)
            continue
        mc_ok,win_rate,quant_reason=quant.evaluate_orb_trade_plan(signal.entry,signal.stop_loss,signal.target,data,
            simulations=SETTINGS.MONTE_CARLO_RUNS,horizon=SETTINGS.MC_HORIZON,min_probability=SETTINGS.MIN_MC_PROBABILITY)
        if not mc_ok:
            logger.info("%s rejected by MC: %s",symbol,quant_reason)
            continue
        success,reason,pos=trader.open_position(symbol,"BUY",signal.entry,signal.stop_loss,signal.target)
        if not success or pos is None:
            logger.info("%s execution rejected: %s",symbol,reason)
            continue
        opened+=1
        try: latest_vwap=float(flow.calculate_vwap(data)["VWAP"].iloc[-1])
        except Exception: latest_vwap=None
        hist=data["Volume"].iloc[:-1].tail(10)
        required=float(hist.mean())*1.2 if not hist.empty else None
        trade_alert(symbol=symbol,side=pos.side,entry=pos.entry,stop_loss=pos.stop_loss,target=pos.target,
            quantity=pos.quantity,risk=pos.risk_per_share*pos.quantity,risk_reward=(pos.target-pos.entry)/(pos.entry-pos.stop_loss),
            mc_probability=win_rate,vwap=latest_vwap,volume=signal.latest_volume,vsa_required_volume=required)
    return {**result,"status":"COMPLETED","layer":5,"trades_opened":opened,"equity":trader.equity,
            "positions":list(trader.positions),"trend":trend,"trend_reason":trend_reason,"macro_reason":macro_reason,"vix":vix}

if __name__=="__main__":
    logger.info("Executing Layer 1 -> Layer 5 AI Trading Bot...")
    print(run_once(NIFTY_50_STOCKS))
