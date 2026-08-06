# Polymarket : Mass Market Maker

> Simultaneously quoting ~2,000 illiquid markets on Polymarket, placing ~2,000 transactions per day, running live on AWS since November 2025.

---

## Strategy

Polymarket hosts over 50,000 prediction markets. The vast majority of these are illiquid, spreads of 20 cents or more are common, and sometimes no one has updated quotes in hours.

My approach is simple and deliberately avoids needing to model the "correct" probability for any individual market:

1. Fetch the current best bid and best ask for a market
2. Place a buy order 1 cent above the best bid and a sell order 1 cent below the best ask
3. Repeat across ~2,000 markets simultaneously, refreshing every 30–60 seconds

**Why this works without probability modeling:**

I'm not taking a view on the outcome, I'm just capturing spread. With 50,000+ markets to choose from, the law of large numbers handles cases where individual fills go against me. Some markets will be unfavorable, but the aggregate is strongly positive.

**Why I focus on illiquid markets:**

Liquid markets on Polymarket have institutional and professional market makers competing with sophisticated pricing models and faster infrastructure. Illiquid markets have almost no competition. The only "cost" is that individual market volumes are low, which is solved by running on thousands of markets simultaneously.

---

## v1 → v2 (currently testing since mid July 2026)
 
**v1** proved the model: a single-process bot polling the REST API on a fixed cycle, applying one quoting rule uniformly across the market universe. It ran profitably for months and is summarized below for reference.
 
**v2** is a from-scratch architectural rebuild, not a tuned version of v1:
 
- **Event-driven, not polled.** Quote decisions fire on WebSocket price ticks instead of a fixed-interval sweep, with market subscriptions sharded across multiple WebSocket connections to scale past what a single connection or REST cycle can support.
- **Strategy split, not one rule.** Markets are routed into distinct sub-strategies (each with independent filters, position sizing, and P&L tracking), rather than one quoting rule applied uniformly.
- **Manipulation-resistant pricing.** Quote prices are bounded relative to depth further down the book, not just top-of-book, to reduce exposure to thin-book spoofing.
- **Self-auditing in production.** Background processes continuously check for duplicate orders and orders on markets that should no longer be traded, and force-correct them without manual intervention.
- **State reconciliation with sanity checks.** Local order/position state is reconciled against the exchange on every cycle, and rejected if it looks like a partial or broken read, instead of being trusted blindly.

---

## Impact of taker fees

In early 2025, Polymarket added fees for takers. This reduced the number of takers on the platform: fewer people crossing the spread means fewer of my orders get filled. Daily transaction count dropped meaningfully after this change. This is visible in the [results graphs](./results.md).

---

## Handling API downtime

Polymarket's API has frequent downtime, at minimum several times per week. Designing around this was essential:

- The bot never crashes on API errors; all requests are wrapped in retry logic with exponential backoff
- State is managed so that stale quotes are not left on the book indefinitely during outages

See [architecture.md](./architecture.md) for the full implementation details.

---

## Results

PnL graphs, transaction volume over time, and videos demonstrating the bot are in [results.md](./results.md).

---

## Files

- [architecture.md](./architecture.md) : how the bot is built: data flow, order management, API handling
- [optimizations.md](./optimizations.md) : how I got the cycle time down to handle 2,000 markets per minute
- [results.md](./results.md) : graphs and numbers
