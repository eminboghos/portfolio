# Architecture : PredictFun Bitcoin Market Maker

## System overview

Three real-time feeds converge into a single quote engine that runs continuously. The entire pipeline from Binance price tick to order submission completes in under 250ms.

---

## Data pipeline

### Binance WebSocket

The primary feed. Receives Bitcoin price updates in real time. The bot is subscribed to the BTC/USDT trade stream, every completed trade triggers a price update.

Each update immediately kicks off a repricing cycle for all active markets.

### Polymarket WebSocket

A secondary feed used exclusively for implied volatility extraction. The bot subscribes to Polymarket's equivalent Bitcoin markets and continuously solves for $\sigma$ (implied volatility) given their quoted prices.

This feed has ~250ms additional latency compared to Binance — which is why it's used for volatility only rather than for direct price copying.

See [black-scholes.md](./black-scholes.md) for the full IV extraction methodology.

### PredictFun WebSocket

The bot connects to PredictFun's WebSocket to receive orderbook updates and fill notifications.

---

## Quote engine

The quote engine runs on every Binance price tick and change of implied volatility:

1. Read current $S_0$ (Bitcoin price) from Binance handler
2. Read current $\sigma_{\text{EMA}}$ from IV extractor
3. For each active market, compute $T$ (time remaining)
4. Apply Black-Scholes to get $P(\text{Up})$
5. Set bid = $P(\text{Up}) - 0.025$, ask = $P(\text{Up}) + 0.025$
6. Check against live orders, if change -> submit order updates

Steps 1–5 are pure computation with no I/O. This completes in under 1ms in Python. The latency budget is entirely step 6 (network).

---

## Latency engineering

### v1 latency: ~400ms

The initial implementation had:
- Sequential order submissions (wait for each API response before the next)
- Synchronous Binance WebSocket handler blocking the quote engine during reconnects
- IV update on every Polymarket tick (some of which are irrelevant)

End-to-end: ~400ms from Binance tick to PredictFun order submitted.

### v3 latency: ~250ms

The critical bug fix: the quote engine was waiting for confirmation from PredictFun's API before processing the next Binance tick. This meant that if the API was slow (100–300ms), multiple Bitcoin moves would be processed late or skipped entirely.

The fix: decouple order submission from the quote computation loop. The quote engine runs on every tick. Order submission happens asynchronously so the engine hands off to a submission worker and immediately returns to wait for the next tick.

Additional improvements:
- Async order submission -> multiple orders submitted concurrently
- Implied volatility update rate-limited to 100ms intervals (not every Polymarket tick, many of which carry no new information)

End-to-end after fixes: ~250ms from Binance tick to order submitted. Most of this is unavoidable network latency.

---

## Order management

Orders are updated when the computed fair value moves more than a tolerance threshold ($0.005 to $0.02 depending on volatility) from the current order price. The threshold is tuned to avoid excessive churn (which wastes API rate limit) while staying close to fair value. 

WS console logs are recorded and available in [results.md](./results.md), showing live order book updates with BTC price and computed probability side by side

---

## PredictFun WebSocket gap handling

The PredictFun WebSocket delivers approximately 98% of events. Missing events could leave the bot with a stale view of the order book.

Gap detection: every message includes a sequence number. The bot tracks the last received sequence number and triggers a resync if a gap is detected.

Resync: a REST call fetches the current orderbook snapshot. The bot rebuilds its in-memory state from the snapshot and continues.


---
