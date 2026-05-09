# PredictFun : Bitcoin Market Maker

> Sub-second market making on Bitcoin up/down prediction markets across 1h, 15min, and 5min time frames. 

---

## Why PredictFun over Polymarket for this strategy?

Polymarket's Bitcoin markets attract institutional market makers with professional infrastructure and large capital. PredictFun is a smaller platform with less competition at my level which means the playing field is more even, and the 2% taker fee on the platform creates a natural spread floor (~4c minimum) that protects market makers without being too restrictive.

---

## Strategy

Bitcoin up/down markets ask: will Bitcoin be higher or lower at some future time than it is right now? The correct probability for "up" changes every time Bitcoin moves.

My approach:

1. Connect to Binance via WebSocket to get real-time Bitcoin prices
2. Use the Black-Scholes model to compute the correct probability of "up" given the current price, time remaining, and implied volatility
3. Place a bid and ask centered on that probability, maintaining a ~5c spread
4. Update quotes whenever the price of Bitcoin moves

The key to accurate pricing is the volatility input : see [black-scholes.md](./black-scholes.md) for how I extract implied volatility from Polymarket's BTC markets rather than using Binance indicators.

---

## Version history and milestones

### v1 : 1-hour markets (12th April 2026)

- Markets: Bitcoin up/down every 1 hour
- Quote latency: ~400ms after BTC price change
- Quote max update speed: 10 times per second
- Volume: ~$100/hour
- Main challenge: setting up the Binance WebSocket pipeline and getting the Black-Scholes computation running fast enough in Python

### v2 : 15-minute markets added (26th April 2026)

When 15-minute markets launched, volume on the platform increased significantly : more traders, more takers, more competition. The 2% taker fee kept the spread floor at ~4c, which preserved margins. Volume jumped to several hundred dollars per hour. This inflection is visible in the [PnL graphs](./results.md).

### v3 : 5-minute markets added (6th May 2026)

5-minute markets are the most volatile : every small Bitcoin move shifts the odds significantly, and quotes go stale faster than in longer-timeframe markets.

While optimizing for this, I found a bug in my quote update path that, when fixed, reduced end-to-end latency from ~400ms to ~250ms. This was a step-change improvement that benefited all three timeframes. Volume jumped to ~$3,000/hour accross all timeframes. I also improved my bot to be able to updates quotes faster (up to 50 times per seconds).

As the 5-minute markets were implemented recently, they remain in the testing phase. I initially underestimated the impact of the increased volatility, which is reflected in the recent PnL dip shown in the [PnL graphs](./results.md).

---

## Maker vs taker

Approximately 70% of my transactions are maker orders. The 30% taker rate is mostly due to my new quotes executing immediately against older resting orders on the orderbook.

---

## PredictFun WebSocket reliability

PredictFun's WebSocket only delivers approximately 98% of events reliably. The bot is built to handle this:

- Missing events are detected by sequence number gaps
- On a detected gap, the bot falls back to a REST snapshot to resync state
- All order logic is designed in a way where receiving a duplicate or missing event never causes incorrect behavior

---

## Files

- [black-scholes.md](./black-scholes.md) : pricing model, volatility extraction from Polymarket
- [architecture.md](./architecture.md) : WebSocket pipeline, order management, latency engineering
- [results.md](./results.md) : PnL graphs, demo videos
