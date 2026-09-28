import logging
from config.settings import SETTINGS
from core.macro_filter import MacroFilter
from core.price_action import PriceActionEngine
from core.quant_engine import build_long_plan
from core.trend_engine import TrendEngine
from data_provider import NSEDataProvider
from execution.paper_trader import PaperTrader
from execution.telegram_notifier import trade_alert

logging.basicConfig(level=logging.INFO)

def run_once(symbols, provider=None, trader=None):
    provider = provider or NSEDataProvider()
    trader = trader or PaperTrader(SETTINGS.DEMO_CAPITAL)

    vix = provider.get_india_vix()
    nifty = provider.get_nifty_daily()
    try:
        trend, trend_reason = TrendEngine().get_trend(nifty)
    except ValueError as exc:
        return {"status": "BLOCKED", "reason": str(exc)}

    allowed, macro_reason = MacroFilter(SETTINGS.VIX_MAX, allow_neutral=False).evaluate_macro_safety(vix, trend)
    if not allowed:
        return {"status": "BLOCKED", "reason": macro_reason, "trend": trend}

    trades = 0
    price_engine = PriceActionEngine(10, 1.5, 1.5)

    for symbol in symbols:
        if trades >= SETTINGS.MAX_TRADES_PER_DAY or symbol in trader.positions:
            break
        data = provider.get_ohlcv(symbol, interval="15m", period="1d")
        if data.empty:
            continue
        signal = price_engine.generate_signal(data)
        if signal.signal != "BUY":
            continue
        plan = build_long_plan(data, trader.equity, SETTINGS.MAX_RISK_PER_TRADE, SETTINGS.MIN_RR, SETTINGS.MIN_MC_PROBABILITY, SETTINGS.MONTE_CARLO_RUNS)
        if plan is None:
            continue
        if trader.open_position(symbol, plan):
            trade_alert(symbol, plan)
            trades += 1

    return {"status":"OK","trend":trend,"trend_reason":trend_reason,"macro_reason":macro_reason,"trades_opened":trades,"equity":trader.equity,"positions":list(trader.positions)}

if __name__ == "__main__":
    print(run_once([]))
