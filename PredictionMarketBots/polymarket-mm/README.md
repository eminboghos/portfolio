# Polymarket — Mass Market Maker

> Simultaneously quoting ~2,000 illiquid markets on Polymarket, placing ~2,000 transactions per day, running live on AWS since November 2024.

---

## Strategy

Polymarket hosts over 50,000 prediction markets. The vast majority of these are illiquid — spreads of 20 cents or more are common, and sometimes no one has updated quotes in hours.

My approach is simple and deliberately avoids needing to model the "correct" probability for any individual market:

1. Fetch the current best bid and best ask for a market
2. Place a buy order 1 cent above the best bid and a sell order 1 cent below the best ask
3. Repeat across ~2,000 markets simultaneously, refreshing every 30–60 seconds

**Why this works without probability modeling:**

I'm not taking a view on the outcome, I'm just capturing spread. With 50,000+ markets to choose from, the law of large numbers handles cases where individual fills go against me. Some markets will be unfavorable, but the aggregate is strongly positive.

**Why I focus on illiquid markets:**

Liquid markets on Polymarket have institutional and professional market makers competing with sophisticated pricing models and faster infrastructure. Illiquid markets have almost no competition. The only "cost" is that individual market volumes are low, which is solved by running on thousands of markets simultaneously.

---

## Key numbers

| Metric | Value |
|---|---|
| Markets quoted simultaneously | ~2,000 |
| Quote refresh interval | 30–60 seconds |
| Daily transactions | ~2,000 |
| Total transactions to date | 200,000+ |
| Platform percentile (PnL + volume) | Top 1% |
| Running since | November 2024 |
| Infrastructure | AWS, Python |

---

## Impact of taker fees

In early 2025, Polymarket added fees for takers. This reduced the number of takers on the platform: fewer people crossing the spread means fewer of my orders get filled. Daily transaction count dropped meaningfully after this change. The bot remains profitable but at lower throughput. This is visible in the [results graphs](./results.md).

---

## Handling API downtime

Polymarket's API has frequent downtime, at minimum several times per week. Designing around this was essential:

- The bot never crashes on API errors; all requests are wrapped in retry logic with exponential backoff
- State is managed so that stale quotes are not left on the book indefinitely during outages

See [architecture.md](./architecture.md) for the full implementation details.

---

## Results

PnL graphs, transaction volume over time, and annotated milestone charts are in [results.md](./results.md).

---

## Files

- [architecture.md](./architecture.md) — how the bot is built: data flow, order management, API handling
- [optimizations.md](./optimizations.md) — how I got the cycle time down to handle 2,000 markets per minute
- [results.md](./results.md) — graphs and numbers
