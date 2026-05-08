# Architecture : Polymarket Market Maker

## System overview

The bot runs as a single Python process on AWS. There is no database, all state is held in memory and reconciled against the live order book on each cycle.

---

## Main loop

The core cycle runs continuously:

1. **Fetch market data** : pull current orderbook snapshots for all markets via the Polymarket REST API
2. **Filter markets** : keep only markets following all criterias
3. **Compute quotes** : for each market, set bid = best_bid + 0.01, ask = best_ask - 0.01
4. **Diff against current orders** : check which quotes have drifted more than the tolerance from live orders
5. **Cancel and replace** : cancel stale orders and submit new ones for markets where the quote has moved
6. **Sleep** : wait until the next cycle (target: full refresh in 30–60 seconds for ~2,000 markets)

---

## Market selection

Markets are selected at startup and periodically refreshed. Criterias are:

- Spread ≥ 20 cents (after my tightening, I still need enough margin to be worth quoting)
- Highest bid > 25 cents (to not enter events that are very unlikely to happen)
- Not resolving in the next 24h (too close to resolution = high adverse selection risk)
- Sufficient volume (at least ~$500 volume/day)

---

## Order management

Each market has at most two live orders at any time : one bid and one ask. The order manager tracks:

- Order ID, side, price, and size for each live order
- Fill history for PnL accounting

On each cycle, orders whose price has drifted by more than 1 cent are cancelled and resubmitted. Orders that haven't been touched in a long time are left in place (not waste any API calls).

---

## API resilience

Polymarket's API has multiple outages per week. The bot handles this gracefully:

- All API calls are retried with exponential backoff (max 3 retries before skipping the market for this cycle)
- A global circuit breaker pauses new order submission if the error rate exceeds a threshold (indicating a platform-wide outage rather than a per-market issue)
- On reconnect, the order tracker reconciles its in-memory state against the live order book to detect any fills that occurred during the outage

The bot doesn't require any manual intervention during an outage, it detects, pauses, and recovers automatically.

---

## Performance

Getting through 2,000 markets in 30–60 seconds requires careful optimization. Details in [optimizations.md](./optimizations.md), but the key levers are:

- Batch API calls wherever the Polymarket API allows it
- Process market data in parallel where possible
- Only recompute quotes for markets where the orderbook has changed since the last cycle
