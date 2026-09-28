from datetime import datetime, timedelta, timezone

import pytest

from execution.paper_trader import PaperTrader


def make_trader(tmp_path, **kwargs):
    return PaperTrader(capital=10000, max_risk_per_trade=150, max_daily_trades=2, cooldown_minutes=30,
                       ledger_path=tmp_path / "trades.csv", state_path=tmp_path / "trader_state.json", min_rr=1.5, **kwargs)


def test_position_sizing_respects_risk_and_cash(tmp_path):
    trader = make_trader(tmp_path)
    qty, risk_per_share = trader.calculate_position_size(100, 95)
    assert risk_per_share == 5
    assert qty == 30
    assert qty * risk_per_share <= 150


def test_open_position_enforces_rr_and_cooldown(tmp_path):
    trader = make_trader(tmp_path)
    ok, _, pos = trader.open_position("TEST", "BUY", 100, 95, 107.5)
    assert ok and pos is not None
    ok, reason, _ = trader.open_position("BAD", "BUY", 100, 95, 107.5)
    assert not ok and "Cooldown" in reason


def test_daily_trade_limit(tmp_path):
    trader = make_trader(tmp_path)
    trader.cooldown_minutes = 0
    assert trader.open_position("AAA", "BUY", 100, 95, 107.5)[0]
    trader.check_and_update_positions({"AAA": 107.5})
    assert trader.open_position("BBB", "BUY", 100, 95, 107.5)[0]
    trader.check_and_update_positions({"BBB": 107.5})
    ok, reason, _ = trader.open_position("CCC", "BUY", 100, 95, 107.5)
    assert not ok and "daily" in reason.lower()


def test_auto_exit_target_persists_cash_and_ledger(tmp_path):
    trader = make_trader(tmp_path)
    ok, _, pos = trader.open_position("EXITME", "BUY", 100, 95, 107.5)
    assert ok and pos
    closed = trader.check_and_update_positions({"EXITME": 108})
    assert len(closed) == 1 and closed[0]["reason"] == "TARGET"
    assert closed[0]["pnl"] == pytest.approx(225)
    assert "EXITME" not in trader.positions
    assert trader.cash == pytest.approx(10225)
    assert "EXITME" in (tmp_path / "trades.csv").read_text()
    assert "positions" in (tmp_path / "trader_state.json").read_text()


def test_auto_exit_stop_loss_and_mtm_equity(tmp_path):
    trader = make_trader(tmp_path)
    ok, _, _ = trader.open_position("MTM", "BUY", 100, 95, 107.5)
    assert ok
    assert trader.get_equity({"MTM": 103}) == pytest.approx(10090)
    closed = trader.check_and_update_positions({"MTM": 94})
    assert closed[0]["reason"] == "STOP_LOSS"
    assert closed[0]["pnl"] == pytest.approx(-150)
    assert trader.get_equity() == pytest.approx(9850)
