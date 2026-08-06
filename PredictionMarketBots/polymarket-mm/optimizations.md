# Performance Optimizations : Polymarket Market Maker

v1's constraint was clear: cycle time scaled with the size of the market universe, because every cycle re-scanned every market over REST. v2 removes that constraint by moving to an event-driven model . But event-driven systems have their own scaling problems: connection limits, race conditions under concurrency, and the risk of reacting to noise. The optimizations below address those.

---

## Key optimizations

### WebSocket sharding
 
A single WebSocket connection can only carry so many subscriptions reliably. Rather than one connection for the full market universe, subscriptions are distributed across multiple shards, each managing its own connection and subscription set. New shards are created on demand as the subscribed universe grows, so the system scales subscription count roughly linearly rather than hitting a hard ceiling.
 
### Subscribe only to what can act
 
Not every market that passes the initial filter can actually result in a trade at the current book state. Rather than subscribing the full filtered universe to live price feeds, v2 pre-computes which markets currently qualify to trade (using the same rule the order-placement logic itself uses) and only subscribes that qualifying subset, then diffs and re-subscribes as qualification changes. This avoids maintaining live subscriptions for markets that couldn't act on a tick even if they moved.
 
### Per-token locking, not a global cycle lock
 
Each market's evaluation runs behind its own lock, not a single lock for the whole system. Ticks for different markets are processed concurrently, a tick for a market that's still being evaluated is queued for a single recheck rather than blocking, and never spawns a pile of duplicate evaluations for the same market.
 
### Cooldowns on replace
 
A market whose price is oscillating slightly, but still within the tolerance the strategy allows, doesn't need to cancel and repost on every tick. A per-market cooldown after a replace prevents rapid-fire cancel/repost cycles that would otherwise burn API calls and rate-limit budget without changing the economics of the quote.
 
### Confirmed cancels before replacement
 
Before posting a replacement order, the cancel of the old order is confirmed via the user WebSocket channel rather than assumed to have succeeded. If confirmation doesn't arrive in time, the system skips posting a replacement for that cycle rather than risking two live orders on the same side of the same market.
 
### Async I/O throughout
 
Both REST calls and order submissions are I/O-bound. Blocking calls are run in a thread pool and awaited alongside the async WebSocket event loop, so a slow response from one market doesn't stall evaluation of others.

---

## AWS instance selection

The choice of AWS region and instance type matters:

- **Region:** eu-west-1 is the closest available AWS server to Polymarket's infrastructure to minimize API round-trip latency
