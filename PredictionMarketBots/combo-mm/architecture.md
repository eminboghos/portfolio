# Architecture: Combo RFQ Market Maker

## System overview

A single async Python process connects to Polymarket's Combo RFQ stream as a maker. Unlike the resting order bots in this repo, there is no quoting cycle : the bot is idle until an RFQ event arrives, then has a narrow window to price and respond.

State (leg prices, open positions, recent quotes) is held in memory and kept current continuously via WebSocket, independent of whether an RFQ is currently in flight, so that when a request does arrive, current prices are already available rather than needing to be fetched cold.

---

## RFQ event flow

1. **RFQ received** : an incoming quote request specifies the combo's legs and a direction
2. **Leg price resolution** : each leg's current price is read from a live WebSocket price cache, keyed by the leg's actual order-book identifier
3. **Gating** : the candidate combo is checked against a series of independent conditions before any price is computed for real
4. **Fair-price computation** : the combo's raw fair value is the product of each leg's live price for known-correlated same-game leg pairs 
5. **Margin application** : the fair value is widened to hit a target edge percentage, producing the price actually quoted
6. **Quote sent** : submitted back to Polymarket, gated by a global kill switch
7. **Leg-watch spawned** : a background task watches all of this quote's legs for price movement until the RFQ resolves (accepted, rejected, expired)
8. **Last Look** : if the requester accepts, a confirmation step follows before the trade finalizes. If a leg moved past the tolerance during that window, the bot cancels.

---

## Margin model

Rather than a flat price offset, margin is expressed as a target edge percentage : expected profit as a fraction of capital actually at risk, which is direction-aware (buying vs selling) and scales with:

- **Leg count** : each additional leg adds incremental margin
- **Time horizon** : legs starting further in the future carry wider margin, tiered by how far ahead the furthest leg in the combo starts

The edge-percentage formulation keeps the actual required profit consistent across very different fair prices and leg counts, rather than the flat-multiplier approach it replaced, which could produce wildly different effective margins for a cheap leg versus an expensive one.

## Risk gates

Every candidate combo passes through gates that are independent of the pricing calculation, checked before a quote is built:

- **Match-start gate** : legs that have already started (or are unresolved) are excluded, legs starting soon are still eligible but priced wider
- **Book-depth gate** : checks depth beyond top-of-book on each leg, not just the best price
- **Position/exposure gate** : global and per-combo exposure limits
- **Extreme-price sanity gate** : rejects candidate prices outside a sane band

