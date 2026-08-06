# Prediction Market Bots

Automated market-making on Polymarket and PredictFun, built entirely in Python on AWS.

## Overview

This repository documents three production trading bots I built and have run continuously since November 2025. All three are live and trading every day.

| Bot | Platform | Mechanism | Markets | Daily transactions | Daily volume | Status | Results |
|---|---|---|---|---|---|---|---|
| [Polymarket MM](./polymarket-mm/) | Polymarket | Resting orders | ~2,000 simultaneously | ~2,000 trades/day | ~$25,000 vol/day | 🟢 Live | [Results](./polymarket-mm/results.md) |
| [PredictFun BTC](./predict_fun-btc/) | PredictFun | Resting orders | 1h / 15min / 5min BTC | ~6,000 trades/day | ~$50,000 vol/day | 🟢 Live | [Results](./predict_fun-btc/results.md) |
| Polymarket Combo RFQ | Polymarket | RFQ (quote-on-request) | Multi-leg sports Combos | ~500 trades/day | ~$15,000 vol/day | 🟢 Live | Results |

All three place me in the top 1% of traders on their respective platforms by PnL and volume.

## Bot 1: Polymarket mass market maker

Illiquid markets on Polymarket often have spreads above 20 cents. I quote inside the best bid and ask on ~2,000 markets simultaneously. With enough markets (50k+) and transactions (200k+), the law of large numbers handles adverse selection without requiring me to model the correct probability for each market individually.

Key challenges solved: processing thousands of markets fast enough to keep quotes current, handling frequent Polymarket API downtime without interruption, running reliably on AWS 24/7 since November 2025.

→ [Full write-up](./polymarket-mm/README.md)

## Bot 2: PredictFun Bitcoin market maker

Market-make the "Bitcoin up or down?" markets on PredictFun across three timeframes (1h, 15min, 5min), maintaining a tight spread and updating quotes within milliseconds of a Bitcoin price move. Pricing uses the Black-Scholes formula with implied volatility extracted from Polymarket's BTC markets.

→ [Full write-up](./redict_fun-btc/README.md)

## Bot 3: Polymarket Combo RFQ market maker

Polymarket's Combo system lets traders request quotes on multi-leg parlays as a single RFQ, rather than trading against a standing order book. This bot watches the RFQ stream and prices incoming requests off live leg prices, responding within the request window and actively cancelling if a leg moves before the trade finalizes.

Unlike the other two bots, there's no book to quote into: the constraint is end-to-end latency and pricing correctness per request, not universe size.

Key milestones:
- **v1** — single sport, non-live matches only
- **v2** — expanded to multiple sports, still non-live matches only
- **v3** — added live matches, across multiple sports
- **v4 (in progress)** — correlated markets: pricing same-game combos (e.g. moneyline + handicap on the same match) as joint probabilities instead of independent legs

→ Full write-up
