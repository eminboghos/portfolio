## Strategy Evolution

The production version of this bot is currently profitable on long-term prediction markets, where liquidity is more stable and prices move more smoothly over time.
I tried to adapt the system to short-term prediction markets, but eventually stopped working on this approach. The main issues came from the market structure itself, not from missing features in the code.
Short-term markets tend to have:
- Very high trading volume compared to available liquidity
- Sudden price spikes caused by small order imbalances
- A lot of competition from other market-making bots running very tight spreads.

Because of this, execution speed and latency matter much more, and small delays quickly turn a strategy unprofitable.

## Experimental bot outcomes

### Experimental bot 1 

The first experimental version added a small directional bias to try to improve fills and capture short-term moves.
This version failed mainly because I underestimated a martingale-like effect. Big losses erased my small gains.


### Experimental bot 2 

The second experimental version reduced directional bias and focused on near-neutral market making.

While risk control was better, the strategy still did not work in practice due to:
- Extremely small profit margins
- Latency and execution delays compared to competitors
- Frequent bad fills during fast price changes

In this environment, even small delays were enough to cancel out expected profits.

## Final decision

Given these constraints, I decided not to continue optimizing short-term strategies.
Instead, I focused my work on the long-term prediction markets where I was already profitable.
