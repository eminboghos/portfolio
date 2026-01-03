# Automated Market-Making Bot

This bot runs on peer-to-peer prediction markets.  
Its goal is not to predict outcomes, but to act as a liquidity provider: it places bids and asks around a fair price, manages inventory, and stays stable across many markets simultaneously.

Most of the work focuses on making the system reliable under real-world conditions, including API failures, partial data, latency, and long runtimes without supervision.

## Software and Automation

This was built as a live system, therefore depending on API support and execution constraints, I implemented the system using Python, TypeScript and JavaScript. 

The bot runs continuously and handles:

- API authentication and key management
- Rate limits and malformed responses
- Retries and recovery after failures
- Safety checks before any order is sent

Once running, it requires no manual intervention.

## Core logic

The bot continuously reads the order books of all the available markets and estimates a fair price based on available liquidity.

It places bid and ask orders around that price.

Spreads and order sizes are adjusted dynamically based on:

- Current inventory
- Liquidity changes
- Market activity

The focus is on consistency and execution quality rather than directional bets.

## Risk management

Risk control is built into the core loop.

This includes:

- Inventory limits per market
- Exposure throttling when market activity is high

The priority is capital preservation, even if that means missing opportunities.

## Scale and results

During live operation, the system executed 50,000+ trades across roughly 6,000 different markets over the past two months and continues to run successfully.

The expected win rate per trade was intentionally close to 50%, reflecting a market-making approach rather than prediction.

Profitability came solely from spread capture and orders filled in very illiquid markets.

Several alternative versions of this bot were tried but execution problems and increasing competition due to growing popularity of prediction markets led to their abandonment.

## Simplified Pseudocode

```python
constraints = {...}  # trading rules and risk limits
all_markets = get_all_available_markets()

for market in all_markets:
    orderbook = get_orderbook(market)
    meets_constraints = determine_if_meets_constraints(orderbook, constraints)
    if meets_constraints:
        update_buy_order()
        update_sell_order()
