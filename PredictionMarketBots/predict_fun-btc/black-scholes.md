# Pricing Model : Black-Scholes with Implied Volatility

## The core formula

Bitcoin up/down markets are essentially binary call options. The probability that Bitcoin closes above the current price at time T is given by the Black-Scholes formula:

$$P(\text{Up}) = \Phi\left(\frac{\ln(S_0/K) + (\mu - \sigma^2/2)T}{\sigma\sqrt{T}}\right)$$

Where:

| Symbol | Meaning |
|---|---|
| $S_0$ | Current Bitcoin price |
| $K$ | Strike price (Bitcoin's price at market open — the reference level) |
| $\mu$ | Drift (implied 0) |
| $\sigma$ | Volatility |
| $T$ | Time remaining until market resolution  |
| $\Phi$ | Cumulative normal distribution function |

$S_0$, $K$ and $T$ are known. The critical unknown is $\sigma$ (volatility).

---

## Why volatility matters

A small change in assumed volatility can shift the computed probability by several percentage points, especially for short-duration markets (5min or 15min). Getting volatility wrong is expensive: I'd be quoting at the wrong price and would get picked off by anyone with a better volatility estimate.

---

## Why I don't use Binance volatility indicators

The obvious approach is to use Binance's realized or implied volatility for Bitcoin. I tried this, and the results were noticeably worse than the alternative below.

The problem is that Binance volatility indicators are backward-looking or computed from options with different structure than these binary markets. They don't cleanly translate to the probability distribution these markets are pricing.

---

## Implied volatility from Polymarket

Polymarket's Bitcoin up/down markets are run by professional and institutional market makers with sophisticated models. Their prices are essentially ground truth for the correct probability.

Rather than modeling volatility from scratch, I work backwards:

1. Observe Polymarket's current price for the equivalent BTC market
2. Treat that price as $P(\text{Up})$
3. Invert the Black-Scholes formula to solve for $\sigma$ given the known $S_0$, $K$, and $T$

This gives me the implied volatility that the professional market makers are pricing in. I recompute this every 100ms as Bitcoin prices and Polymarket quotes update and smooth the found values using an exponential moving average with a 60-second half-life

---

## Validation

I have video recordings showing side-by-side comparisons of:
- My computed probability vs Polymarket's displayed price
- The timestamp difference between a Bitcoin move and each platform updating

The probability values are consistently within 1–2% of each other. My updates arrive measurably earlier when Bitcoin makes a sharp move.

See [media/videos/](../../media/videos/) for the recordings.

---

## In practice

After every Binance WebSocket tick:

1. Receive new $S_0$ from Binance
2. Compute $P(\text{Up})$ using current $\sigma_{\text{EMA}}$ and $T$
3. Compute new bid = $P(\text{Up}) - 0.025$ and ask = $P(\text{Up}) + 0.025$ (maintaining 5c spread)
4. Submit order updates if quotes have moved more than the tolerance

Steps 2 and 3 complete in well under 1ms. The latency budget is dominated by network round-trips to PredictFun and Binance servers.
