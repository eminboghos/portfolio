# Polymarket Combo RFQ Market Maker

Automated maker for Polymarket's Combo (parlay) RFQ system : quoting multi-leg, multi-sport combos in real time as requests arrive.

## What a Combo is, and why it's a different problem

A Combo lets a trader bet on multiple legs at once (two tennis moneylines) as a single parlay-style position. Polymarket runs this as a request-for-quote (RFQ) market, not a standing order book: a trader submits a request for a specific combination, and makers have a short window to respond with a price before the requester accepts, rejects, or lets it expire.

This is a different problem from resting-order market making:

- There's no book to post into so the bot must compute a fair price and respond within the RFQ's window, so latency is a first-class constraint, not just an optimization
- A combo's "fair price" isn't quoted anywhere; it has to be derived from the individual legs live prices
- Some leg pairs from the same game are structurally correlated (a match's moneyline and its set handicap), and pricing them as independent would misprice the combo
- There's a final confirmation step ("Last Look") after a quote is accepted, during which a leg can move before the trade is finalized, the bot has to actively watch for that and pull the quote if it does

## Evolution

The bot was built up in stages, each widening what it's willing to quote on:

- **v1** : single sport, non-live matches only
- **v2** : multiple sports, non-live matches only
- **v3** : live matches added, across multiple sports
- **v4 (in progress)** : correlated same-game combos: pricing structurally related leg pairs (moneyline + handicap on the same match) as a joint probability rather than a independent product

## Approach

- Subscribe to live order-book prices for every leg via WebSocket (not the slower Gamma API, which is only used as a display/metadata fallback, never to price a live quote)
- On an incoming RFQ, resolve each leg's fair price from live ticks only. If any leg's price hasn't been confirmed by a live WS tick, the whole combo is skipped rather than quoted off a stale fallback
- Compute the combo's raw fair value as the product of leg prices (currently only quoting combos with all independent legs)
- Widen that fair value to a target profit margin, expressed as a percentage of capital at risk, not a flat price offset. Scaled up for combos with legs further out in time and for additional legs
- Run the quote through a series of independent gates (position exposure, book depth, match start timing, extreme-price sanity, resend/spam throttling) before sending
- After sending, watch all legs live. If any leg's price drifts materially before the requester confirms, cancel the quote rather than risk being picked off

## Key numbers

| Metric | Value |
|---|---|
| Sports / market types | Multiple sports, live + non-live matches |
| Mechanism | RFQ (request-for-quote), not resting orders |
| Target end-to-end quote latency | < 400 ms |
| Daily quotes sent | ~500,000 |
| Daily trades | ~500 |
| Daily volume | ~$15,000 |
| Running since | mid July 2026 |
| Infrastructure | AWS, Python |
