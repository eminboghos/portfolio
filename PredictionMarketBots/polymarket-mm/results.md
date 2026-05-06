# Results — Polymarket Market Maker

## Summary

Running since November 2024. Consistently top 1% of Polymarket traders by PnL and volume. ~2,000 transactions per day on average across the bot's lifetime.

---

## Graphs

> **📊 Add your images here.** Suggested captions are below each placeholder.

### PnL over time

![PnL graph — replace with your image](../../media/pnl-graphs/polymarket-pnl.png)

*Cumulative PnL from November 2024 to present. The slope is consistent, with a visible flattening after taker fees were introduced in early 2025.*

---

### Daily transaction count

![Transaction volume graph — replace with your image](../../media/charts/polymarket-daily-txns.png)

*Number of fills per day. The drop-off after taker fee introduction is clearly visible. The bot continues placing orders daily.*

---

### Markets quoted over time

![Markets graph — replace with your image](../../media/charts/polymarket-markets.png)

*Number of markets actively quoted simultaneously. Settled at ~2,000 after initial scaling.*

---

## Milestones

| Date | Event |
|---|---|
| November 2024 | Bot launched, initial testing on ~100 markets |
| December 2024 | Scaled to ~2,000 markets, full automation |
| January 2025 | 100,000 total transactions milestone |
| Early 2025 | Polymarket introduces taker fees — daily transaction count drops |
| May 2025 | 200,000+ total transactions, bot still running |

---

## Platform ranking

Top 1% by PnL and by total volume among all Polymarket traders. These metrics are visible on the Polymarket leaderboard.

---

## Notes on PnL

PnL is calculated from fills — the difference between the price at which I sold shares and the price at which I bought them, net of any fees. Because I quote both sides of the market, I capture spread when both sides fill. The strategy is market-neutral: I have no directional view on any outcome.

Adverse selection (filling at a bad price because someone with better information is on the other side) is the main risk. This is mitigated by:
- Only quoting illiquid markets where sophisticated informed traders are rare
- Diversifying across thousands of markets so any single adverse fill is small
- The wide initial spread providing a buffer even on unfavorable fills
