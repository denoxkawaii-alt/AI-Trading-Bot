# AI-Trading-Bot

Indian NSE/BSE intraday paper-trading engine.

**Rules:** ₹10,000 demo capital, ₹150 max planned risk/trade, max 2 trades/day,
30-minute cooldown parameter, no duplicate position, minimum RR 1:2.5.

**Layers:** Nifty/India VIX macro filter; liquidity sweep; 1D/15m/5m price action;
2x volume breakout; bid/ask imbalance; ATR sizing; 1,000-path Monte Carlo
confidence gate; Telegram alerts.

The 85% Monte Carlo value is a filter derived from return-resampling assumptions,
not a guaranteed win probability. Real NSE/BSE and Level-2 data require a suitable
licensed provider adapter. This repository does not place live orders.

Install: `pip install -r requirements.txt`; then provide normalized CSV demo data
or implement MarketDataProvider for your chosen data source.