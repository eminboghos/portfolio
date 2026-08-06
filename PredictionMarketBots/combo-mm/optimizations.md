# Performance Optimizations: Combo RFQ Market Maker

Since there's no quoting cycle to optimize, the constraint here is different from the other bots in this repo: every RFQ has a real response window, so the cost that matters is end-to-end latency from "request received" to "quote sent," plus not letting one slow operation stall the whole event loop.

---

## Key optimizations

### WebSocket pooling for order books

Leg prices are kept warm continuously via a pool of WebSocket connections rather than fetched fresh per RFQ, so a request never waits on a cold price lookup.

### Event-loop lag watchdog

A dedicated background task periodically measures how long the async event loop takes to get back to a trivial scheduled callback. If that lag exceeds a threshold, it's a signal that something elsewhere in the process is blocking the loop.

### Latency circuit breaker

If recent order-book fetch latency degrades past a threshold, the bot stops sending new quotes rather than continuing to quote off increasingly stale data during a slow patch, the same philosophy as the platform-wide circuit breaker in the other bots, applied to latency instead of error rate.

### Connection recycling

Long-lived HTTP/WS connections are periodically recycled rather than held indefinitely, avoiding the slow degradation that can accumulate on connections kept open for very long periods.

