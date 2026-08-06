# Architecture : Polymarket Market Maker

## System overview

The bot runs as a single Python process on AWS, using asyncio throughout. There is no database; state (live orders, positions, market data) is held in memory and continuously reconciled against the exchange.

v1 drove decisions from a fixed-interval REST polling loop. v2 replaces that with an event-driven design: market data arrives over WebSocket, and each price change triggers an independent evaluation for the affected market.

---

## Main loop

1. **Market discovery** : the market universe is fetched and filtered via REST on a periodic basis (new markets appear, old ones close continuously)
2. **WebSocket subscription** : qualifying markets are subscribed to a live price-tick feed, sharded across multiple WebSocket connections to scale subscription count beyond what a single connection supports
3. **Per-token evaluation** : each price tick triggers an isolated evaluation of that market only (buy-side and sell-side), gated by a per-token lock so overlapping ticks for the same market never race each other
4. **Order diff and execution** : the evaluation computes whether the live order (if any) still satisfies the strategy's rules; if not, it cancels and replaces, with cancels confirmed via the user WebSocket channel before a replacement is posted
5. **Continuous reconciliation** : order and position state is independently re-synced against the exchange on a rolling basis, not just derived from local WS events

---

## Market selection

Markets are selected at startup and periodically refreshed. Criteria are:

- Spread ≥ 10 cents (after my tightening, I still need enough margin to be worth quoting)
- Highest bid > 25 cents (to not enter events that are very unlikely to happen)
- Not resolving in the next 24h (too close to resolution = high adverse selection risk)
- Sufficient volume (at least ~$500 volume/day)

These criterias change overtime due to changing market conditions and increased competition.

---
 
## Strategy routing
 
Rather than one quoting rule applied uniformly, v2 routes each qualifying market into one of several sub-strategies based on its current book shape and metadata (event type, time to resolution, spread, bid level). Each sub-strategy has independent:
 
- Entry filters
- Position sizing logic
- Depth requirements before it will quote
- P&L and exposure tracking
  
This lets the system apply materially different risk tolerance to, say, a market resolving in days on a settled-looking outcome versus a fast-moving sports market close to game time, instead of forcing both through the same rule.

---
 
## Order management
 
Each market carries at most one live bid and one live ask. The order manager tracks order ID, side, price, and size per market, and fill history for P&L accounting.
 
Two safeguards sit on top of the base logic:
 
- **Depth-aware pricing.** Quote prices are bounded relative to book depth beyond the top level, not just the best bid/ask, to reduce exposure to a thin book where a single order at the top isn't representative of real interest.
- **Concurrency-safe exposure caps.** Buy-side exposure is capped by a reserve-then-confirm mechanism: a slot is atomically reserved the instant a decision is made to place an order, before the network call happens, and released on success or failure. 

---

## API resilience

Polymarket's REST API has multiple outages per week, the WebSocket connections can also drop or go silent therefore v2 handles both:
 
- All REST calls are wrapped in retry logic with exponential backoff
- A circuit breaker pauses new order submission if the error rate spikes platform-wide, rather than continuing to retry into an outage
- The market-data WebSocket and the separate user-data WebSocket (fills/order updates) both auto-reconnect on drop
- The user WebSocket carries a watchdog timeout: if no message arrives within the expected window, the connection is assumed dead and is forced to reconnect, rather than silently going stale
- On reconnect, in-memory order/position state is reconciled against the live book to catch anything that happened during the disconnect
No manual intervention is required to detect, pause through, and recover from an outage.
 
---

