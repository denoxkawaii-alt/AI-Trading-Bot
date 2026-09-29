import logging
import time
from datetime import datetime, time as dt_time, timedelta
from typing import Callable, Optional
from pathlib import Path
from zoneinfo import ZoneInfo

from config.settings import SETTINGS
from config.stock_universe import fetch_nse_universe
from core.macro_filter import MacroFilter
from core.ai_engine import AITradingEngine
from api.health_server import start_health_server
from core.order_flow import OrderFlowEngine
from core.price_action import PriceActionEngine
from core.quant_engine import QuantEngine
from core.trend_engine import TrendEngine
from data_provider import NSEDataProvider
from execution.paper_trader import PaperTrader
from execution.telegram_bot import TelegramCommandBot
from execution.telegram_notifier import exit_alert, trade_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)


def is_market_open(now: Optional[datetime] = None) -> bool:
    current = (now or datetime.now(IST)).astimezone(IST)
    return current.weekday() < 5 and MARKET_OPEN <= current.time() <= MARKET_CLOSE


def _completed_15m_candles(data, now: Optional[datetime] = None):
    if data is None or data.empty:
        return data
    current = (now or datetime.now(IST)).astimezone(IST)
    last_index = data.index[-1]
    if last_index.tzinfo is None:
        last_index = last_index.replace(tzinfo=IST)
    else:
        last_index = last_index.astimezone(IST)
    if last_index + timedelta(minutes=15) > current:
        return data.iloc[:-1]
    return data


def _current_position_prices(provider: NSEDataProvider, trader: PaperTrader) -> dict[str, float]:
    prices: dict[str, float] = {}
    for symbol, position in trader.positions.items():
        data = provider.get_ohlcv(symbol, interval="1m", period="1d")
        if data is None or data.empty:
            continue
        latest = data.iloc[-1]
        high, low, close = float(latest["High"]), float(latest["Low"]), float(latest["Close"])
        if low <= position.stop_loss:
            prices[symbol] = position.stop_loss
        elif high >= position.target:
            prices[symbol] = position.target
        else:
            prices[symbol] = close
    return prices


def _new_trader() -> PaperTrader:
    data_dir = Path(SETTINGS.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Trading data directory: %s", data_dir.resolve())
    return PaperTrader(
        capital=SETTINGS.DEMO_CAPITAL,
        max_risk_per_trade=SETTINGS.MAX_RISK_PER_TRADE,
        max_daily_trades=SETTINGS.MAX_TRADES_PER_DAY,
        cooldown_minutes=SETTINGS.COOLDOWN_MINUTES,
        ledger_path=data_dir / "trades.csv",
        state_path=data_dir / "trader_state.json",
        min_rr=SETTINGS.MIN_RR,
    )


def run_once(symbols: list[str], provider: Optional[NSEDataProvider] = None,
             trader: Optional[PaperTrader] = None, now: Optional[datetime] = None) -> dict:
    provider = provider or NSEDataProvider()
    trader = trader or _new_trader()
    result = {"status": "STARTING", "layer": 0, "trades_opened": 0,
              "equity": trader.get_equity(), "positions": list(trader.positions)}
    vix = provider.get_india_vix()
    if vix is None:
        return {**result, "status": "BLOCKED", "layer": 1, "reason": "India VIX unavailable. Failing closed."}
    if vix > SETTINGS.VIX_MAX:
        return {**result, "status": "BLOCKED", "layer": 1,
                "reason": f"India VIX too high: {vix:.2f} > {SETTINGS.VIX_MAX:.2f}"}
    nifty = provider.get_nifty_daily()
    if nifty is None or nifty.empty:
        return {**result, "status": "BLOCKED", "layer": 2, "reason": "Nifty data unavailable."}
    try:
        trend, trend_reason = TrendEngine().get_trend(nifty)
    except ValueError as exc:
        return {**result, "status": "BLOCKED", "layer": 2, "reason": str(exc)}
    allowed, macro_reason = MacroFilter(SETTINGS.VIX_MAX, allow_neutral=False).evaluate_macro_safety(vix, trend)
    if not allowed:
        return {**result, "status": "BLOCKED", "layer": 2, "reason": macro_reason, "trend": trend}
    price = PriceActionEngine(volume_lookback=10, volume_multiplier=1.5, min_risk_reward=SETTINGS.MIN_RR)
    flow = OrderFlowEngine(vwap_confirmation=True, volume_multiplier=1.2, min_avg_volume=1000.0)
    ai = AITradingEngine(SETTINGS.AI_MIN_CONFIDENCE)
    quant = QuantEngine(default_simulations=SETTINGS.MONTE_CARLO_RUNS, default_horizon=SETTINGS.MC_HORIZON,
                        default_min_probability=SETTINGS.MIN_MC_PROBABILITY)
    opened = 0
    for raw in symbols:
        symbol = raw.strip().upper()
        if not symbol or trader.daily_trade_count >= SETTINGS.MAX_TRADES_PER_DAY:
            break
        ok, _ = trader.can_trade(symbol)
        if not ok:
            continue
        data = _completed_15m_candles(provider.get_ohlcv(symbol, interval="15m", period="1d"), now=now)
        if data is None or data.empty:
            continue
        signal = price.generate_signal(data)
        if signal.signal != "BUY":
            continue
        flow_ok, flow_reason = flow.validate_order_flow(data, "BUY", 10)
        if not flow_ok:
            logger.info("%s rejected by Layer 4: %s", symbol, flow_reason)
            continue
        try:
            vwap_for_ai = float(flow.calculate_vwap(data)["VWAP"].iloc[-1])
        except Exception:
            vwap_for_ai = None
        ai_decision = ai.evaluate_buy(data, vwap_for_ai)
        if SETTINGS.AI_ENABLED and ai_decision.signal != "BUY":
            logger.info("%s rejected by AI layer: %.1f%% - %s", symbol, ai_decision.confidence * 100, ai_decision.reason)
            continue
        mc_ok, win_rate, quant_reason = quant.evaluate_orb_trade_plan(
            signal.entry, signal.stop_loss, signal.target, data,
            simulations=SETTINGS.MONTE_CARLO_RUNS, horizon=SETTINGS.MC_HORIZON,
            min_probability=SETTINGS.MIN_MC_PROBABILITY)
        if not mc_ok:
            logger.info("%s rejected by MC: %s", symbol, quant_reason)
            continue
        success, reason, pos = trader.open_position(symbol, "BUY", signal.entry, signal.stop_loss, signal.target)
        if not success or pos is None:
            logger.info("%s execution rejected: %s", symbol, reason)
            continue
        opened += 1
        try:
            latest_vwap = float(flow.calculate_vwap(data)["VWAP"].iloc[-1])
        except Exception:
            latest_vwap = None
        hist = data["Volume"].iloc[:-1].tail(10)
        required = float(hist.mean()) * 1.2 if not hist.empty else None
        trade_alert(symbol=symbol, side=pos.side, entry=pos.entry, stop_loss=pos.stop_loss, target=pos.target,
                    quantity=pos.quantity, risk=pos.risk_per_share * pos.quantity,
                    risk_reward=(pos.target-pos.entry)/(pos.entry-pos.stop_loss), mc_probability=win_rate,
                    vwap=latest_vwap, volume=signal.latest_volume, vsa_required_volume=required)
    live_prices = _current_position_prices(provider, trader) if trader.positions else {}
    return {**result, "status": "COMPLETED", "layer": 5, "trades_opened": opened,
            "equity": trader.get_equity(live_prices), "positions": list(trader.positions), "trend": trend,
            "trend_reason": trend_reason, "macro_reason": macro_reason, "vix": vix}


def run_autonomous(symbols: Optional[list[str]] = None, provider: Optional[NSEDataProvider] = None,
                   trader: Optional[PaperTrader] = None, cycle_seconds: int = 60,
                   universe_refresh_minutes: int = 15, max_cycles: Optional[int] = None,
                   sleep_fn: Callable[[float], None] = time.sleep,
                   now_fn: Callable[[], datetime] = lambda: datetime.now(IST)) -> None:
    provider = provider or NSEDataProvider()
    trader = trader or _new_trader()
    current_symbols = symbols
    last_universe_refresh: Optional[datetime] = None
    cycles = 0
    while True:
        now = now_fn().astimezone(IST)
        # Railway starts this worker at 09:00 IST; keep it alive only until 16:00 IST.
        if now.time() >= dt_time(16, 0):
            logger.info("Trading worker session ended at 16:00 IST. Exiting until next scheduled start.")
            return
        if is_market_open(now):
            monitor_prices = _current_position_prices(provider, trader)
            closed = trader.check_and_update_positions(monitor_prices)
            for trade in closed:
                exit_alert(symbol=trade["symbol"], side=trade["side"], quantity=trade["quantity"],
                           entry=trade["entry"], exit_price=trade["exit"], pnl=trade["pnl"], reason=trade["reason"])
            refresh_due = (current_symbols is None or last_universe_refresh is None or
                           (now-last_universe_refresh).total_seconds() >= universe_refresh_minutes*60)
            if refresh_due:
                current_symbols = fetch_nse_universe()
                last_universe_refresh = now
                logger.info("Universe ready: %d symbols.", len(current_symbols))
            try:
                run_once(current_symbols, provider=provider, trader=trader, now=now)
            except Exception:
                logger.exception("Autonomous trading cycle failed; continuing after cooldown.")
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                return
            sleep_fn(max(1, cycle_seconds))
        else:
            logger.info("NSE market closed (%s IST). Worker is alive until 16:00 IST; next check in 30s.", now.strftime("%Y-%m-%d %H:%M:%S"))
            if max_cycles is not None and cycles >= max_cycles:
                return
            sleep_fn(30)


if __name__ == "__main__":
    logger.info("Starting autonomous Layer 1 -> Layer 5 paper-trading engine...")
    start_health_server(SETTINGS.HEALTH_PORT)
    trader = _new_trader()
    telegram_bot = TelegramCommandBot(trader, SETTINGS.DATA_DIR)
    telegram_bot.start()
    run_autonomous(trader=trader)
