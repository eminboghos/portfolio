# Performance Optimizations : Polymarket Market Maker

The core challenge is to cycle through ~2,000 markets, compare order book state, compute new quotes, and submit changes, all within 30–60 seconds, using a single Python process talking to a rate-limited REST API.

---

## Key optimizations

### Batch fetching

Polymarket's API supports fetching multiple markets in a single request. Rather than 2,000 individual calls, the bot groups markets into batches and fetches them in parallel. This alone cuts fetch time by an order of magnitude.

### Change detection

Most markets don't change between cycles. Rather than recomputing and resubmitting quotes for all 2,000 markets every cycle, the bot tracks the last-seen best bid and ask for each market and only acts on markets where something has changed.

In practice, only a small fraction of markets move in any 60 second window so the effective work per cycle is much less than 2,000 markets.

### Deferred cancellation

Canceling an order costs an API call. If a quote has drifted slightly but is still within tolerance, the bot leaves the existing order in place rather than canceling and resubmitting. This reduces the number of API calls per cycle significantly.

### Parallel order submission

Order submissions are I/O-bound (waiting for the API response). The bot uses async I/O to submit multiple orders concurrently, rather than waiting for each one sequentially.

---

## Cycle time results

The bot comfortably refreshes all 2,000 markets every 30–60 seconds, with headroom to add more markets.

---

## AWS instance selection

The choice of AWS region and instance type matters:

- **Region:** eu-west-1 is the closest available AWS server to Polymarket's infrastructure to minimize API round-trip latency
