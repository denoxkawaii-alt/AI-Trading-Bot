import pandas as pd

from core.order_flow import OrderFlowEngine


def make_data(volumes):
    n = len(volumes)
    return pd.DataFrame({"Open": [100.0]*n, "High": [102.0]*n, "Low": [99.0]*n,
                         "Close": [101.0]*n, "Volume": volumes})


def test_vsa_uses_previous_candles_not_breakout_candle():
    volumes = [1000] * 10 + [2000]
    engine = OrderFlowEngine(vwap_confirmation=False, volume_multiplier=1.2, min_avg_volume=500)
    ok, reason = engine.validate_order_flow(make_data(volumes), "BUY", volume_ma_period=10)
    assert ok
    assert "HistoricalAvg=1000" in reason
    assert "Required=1200" in reason


def test_vsa_rejects_insufficient_volume_spike():
    volumes = [1000] * 10 + [1100]
    engine = OrderFlowEngine(vwap_confirmation=False, volume_multiplier=1.2, min_avg_volume=500)
    ok, reason = engine.validate_order_flow(make_data(volumes), "BUY", volume_ma_period=10)
    assert not ok
    assert "VSA threshold" in reason
