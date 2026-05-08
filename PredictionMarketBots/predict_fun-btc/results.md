# Results — PredictFun Bitcoin Market Maker

## Summary

Three distinct performance phases, each clearly visible in the PnL and volume graphs. The biggest step-changes were adding 15-minute markets (volume increase) and fixing the 20ms latency bug (volume and PnL both jump sharply).

---

## Graphs

> **📊 Add your images here.** Suggested captions below each placeholder.

### PnL over time (annotated)

![PnL graph — replace with your image](../../media/pnl-graphs/predictfun-pnl-annotated.png)

*Cumulative PnL with three labeled milestones: (1) launch with 1h markets, (2) 15min markets added, (3) 5min markets + 20ms latency fix. The slope increases at each milestone.*

---

### Volume per hour

![Volume graph — replace with your image](../../media/charts/predictfun-volume-per-hour.png)

*Hourly volume from launch to present. The jump from ~100/hr to ~3,000/hr between v1 and v3 is the main story.*

---

### Quote latency over time

![Latency graph — replace with your image](../../media/charts/predictfun-latency.png)

*End-to-end quote update latency (ms from Binance tick to PredictFun order submitted). The drop from ~400ms to ~20ms at the v3 fix is clearly visible.*

---

### My price vs Polymarket price

![Price comparison — replace with your image](../../media/charts/predictfun-vs-polymarket-price.png)

*Side-by-side comparison of my computed P(Up) vs Polymarket's displayed price. The two track closely (within 1–2%), validating the IV extraction methodology. My price updates arrive earlier on sharp Bitcoin moves.*

---

### Maker vs taker breakdown

![Maker/taker pie or bar — replace with your image](../../media/charts/predictfun-maker-taker.png)

*~70% maker, ~30% taker across all transactions. Maker orders capture the spread; taker orders are used when I need to hedge or adjust quickly.*

---

## Version timeline

| Version | Date | Key change | Volume/hr |
|---|---|---|---|
| v1 | November 2024 | 1h markets, ~400ms latency | ~100 |
| v2 | Early 2025 | 15min markets added | ~500 |
| v3 | Early 2025 | 5min markets + 20ms latency fix | ~3,000 |

---

## Videos

The following videos are in [media/videos/](../../media/videos/):

- **AWS console live view** — real-time logs of all order placements, cancellations, and fills with millisecond timestamps, share count, and expected value
- **Price comparison** — split screen showing my computed P(Up), Polymarket's displayed price, and the current Bitcoin price. Demonstrates both the accuracy and the latency advantage
- **Order book view** — live PredictFun order book with my bids and asks visible, updating as Bitcoin moves
