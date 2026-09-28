# AI-Trading-Bot

Indian NSE intraday paper-trading/research engine.

## Current 5-Layer architecture

- **Layer 1 — Macro safety:** India VIX must be available and **<= 22.00**; VIX above 22 blocks new entries.
- **Layer 2 — Trend:** Nifty EMA20/EMA50. Close > EMA50 and EMA20 > EMA50 = BULLISH; Close < EMA50 and EMA20 < EMA50 = BEARISH; otherwise NEUTRAL and new entries are blocked.
- **Layer 3 — 15-minute ORB:** first 15-minute candle defines the opening range; latest completed candle must close above the opening high and volume must exceed **1.5x the previous 10 candles' average**. Stop = breakout candle low, with opening-range low fallback. Minimum **R:R = 1:1.5**.
- **Layer 4 — OHLCV order-flow/VSA:** VWAP confirmation plus breakout volume >= **1.2x** the previous 10-candle average and a minimum historical average volume filter.
- **Layer 5 — Paper execution:** **₹10,000** default demo capital, **₹150 maximum risk/trade**, **2 trades/day**, **30-minute cooldown**, duplicate-position protection, persistent state, CSV trade ledger, automatic SL/Target exits, mark-to-market equity, and optional Telegram alerts.
- **Quant gate:** 1,000 Monte Carlo paths with an 85% minimum probability threshold. This is a statistical filter, not a guaranteed prediction and does not overwrite ORB entry/SL/target.

## Autonomous engine

main.py stays alive continuously, operates on the NSE market window **09:15–15:30 IST**, monitors active paper positions at the start of every cycle, sends exit alerts, refreshes the dynamic NSE universe, and scans eligible symbols.

The dynamic universe starts from NSE's equity master list, keeps regular EQ series, then applies the configured minimum price (**₹10**) and average daily volume (**100,000 shares**) filters using recent daily research quotes. If the dynamic universe cannot be built, the engine falls back to the Nifty 50 list.

## Data and safety

This repository is **paper trading only** and does not place live broker orders. Yahoo Finance is a research/paper-data source, not exchange/broker-grade execution infrastructure. Intraday SL/Target monitoring is simulated and can differ from actual exchange fills. The Monte Carlo probability is a model gate, not a guaranteed win probability.

## Tests

Run:

    pip install -r requirements.txt
    pytest -q

Tests cover position sizing, risk limits, daily trade limits, cooldowns, automatic exits, mark-to-market equity, and VSA volume validation.

## Usage

    python main.py

Keep Telegram credentials in environment variables:

    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_CHAT_ID=...

No live broker order is sent by this repository.
