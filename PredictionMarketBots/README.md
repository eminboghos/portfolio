# Prediction Market Bots
 
> Automated market-making on Polymarket and PredictFun built entirely in Python on AWS.
 
---
 
## Overview
 
This repository documents two production market-making bots I built and have run continuously since November 2024. Both bots are live and placing orders every day.
 
| Bot | Platform | Markets | Daily transactions | Status |
|---|---|---|---|---|
| [Polymarket MM](./polymarket-mm/) | Polymarket | ~2,000 simultaneously | ~2,000 trades/day | 🟢 Live |
| [PredictFun BTC](./predictfun-btc/) | PredictFun | 1h / 15min / 5min BTC | ~$25,000 vol/day | 🟢 Live |
 
Both bots place me in the **top 1% of traders** on their respective platforms by PnL and volume.
 
---
 
## Bot 1 — Polymarket mass market maker
 
**Concept:** Illiquid markets on Polymarket often have big spreads above 20 cents (20% of the price range). I quote 1 cent inside the best bid and ask on ~2,000 markets simultaneously, updating every 30–60 seconds. With enough markets (50k+) and transactions (200k+), the law of large numbers handles adverse selection without requiring me to model the correct probability for each market.
 
**Key challenges solved:**
- Processing 2,000+ markets fast enough to cycle through all quotes in under 60 seconds
- Handling Polymarket API downtime (happens multiple times per week) without bot interruption
- Running reliably on AWS 24/7 since November 2024
→ [Full write-up](./polymarket-mm/README.md)
 
---
 
## Bot 2 — PredictFun Bitcoin market maker
 
**Concept:** Market-make the "Bitcoin up or down?" markets on PredictFun across 3 timeframes (1h, 15min, 5min). I maintain a ~5c spread and update quotes in under 400ms after a Bitcoin price move. Pricing uses the Black-Scholes formula with implied volatility extracted from Polymarket's BTC markets.
 
**Key milestones:**
- v1 (12th April) : 1h markets, ~$100 volume/hour, 10 updates/s
- v2 (28th April) : 15min markets added, volume jumps significantly
- v3 (5th May)    : 5min markets added, ~$3,000 volume/hour, 50 updates/s

→ [Full write-up](./predictfun-btc/README.md)
