# AI-Trading-Bot

Indian NSE intraday paper-trading/research engine.

Current stack:
- Layer 1: India VIX maximum 22 and Nifty trend safety filter.
- Layer 2: Nifty EMA20/EMA50 trend engine.
- Layer 3: 15-minute ORB + 1.5x volume spike.
- Quant gate: ATR sizing, ₹150 maximum planned risk/trade, minimum RR 1:2.5, 1,000-path Monte Carlo filter.
- Execution: simulated paper trader and optional Telegram alerts.

Layer 2:
Close > EMA50 and EMA20 > EMA50 = BULLISH.
Close < EMA50 and EMA20 < EMA50 = BEARISH.
Otherwise = NEUTRAL.

Layer 3:
First 15-minute candle defines the opening range.
Latest close must be above opening-range high.
Latest volume must exceed 1.5x the previous 10 candles average.
ORB stop is the breakout candle low, with opening-range low as fallback.
ORB target is minimum 1:1.5. The quant layer can require the stricter configured 1:2.5 RR.

Safety:
This repository is paper trading only and does not place live orders. Yahoo Finance is not a broker-grade execution feed. Monte Carlo probability is a model filter, not a guaranteed win probability.

Production work still required:
licensed/appropriate market data, exchange calendar/session validation, persistent cooldown/day state, complete tests, monitoring, and broker execution controls.

Install:
pip install -r requirements.txt

Use run_once() with an NSE symbol list such as RELIANCE or TCS.
