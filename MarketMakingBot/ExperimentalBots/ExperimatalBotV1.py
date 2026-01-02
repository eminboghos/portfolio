import requests
import threading
from datetime import datetime, timedelta, timezone
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams, TradeParams, OpenOrderParams
from py_clob_client.clob_types import ApiCreds, OrderArgs, PartialCreateOrderOptions, OrderType, PostOrdersArgs, MarketOrderArgs
from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
from py_clob_client.exceptions import PolyException
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import eth_account
from eth_account.messages import encode_defunct
from web3 import Web3
from eth_account import Account
import subprocess
import os
from eth_utils import to_bytes
import sympy as sp

POSITION_SIZE = 5
MIN_TRADE_SIZE = 550
MAX_SPENT_SECURITY = 570
SPENT_LEVEL_1 = 120
SPENT_LEVEL_2 = 250
SPENT_LEVEL_3 = 560
MARKET = "btc"
TIMEFRAME = "15m"

all_placed_buy_orders = []
current_markets = []
markets_final = []
buy_order_markets = []
sell_order_markets = []
tracked_buy_orders = []
tracked_sell_orders = []
current_positions = []
current_buy_orders = []
lowest_bid_placed = 0.05
upSize = 999
downSize = 999
STRAT_STATE = {}
STRAT_FILLED = {}

s = STRAT_STATE.setdefault("", {
    "yes_shares": Decimal(0),
    "no_shares": Decimal(0),
    "spent_yes": Decimal(0),
    "spent_no": Decimal(0),
    "last_minute": -1,
    "last_20s_ts": 0,
    "last_winner": "None",
    "sell_all_price": Decimal(1),
    "can_trade": True,
    "liquidated": False,
    "num_flips": 0,
    "num_limit_orders": 0,
    "num_market_orders": 0,
    "num_orders": 0
})

s_filled = STRAT_FILLED.setdefault("", {
    "yes_shares": Decimal(0),
    "no_shares": Decimal(0),
    "spent_yes": Decimal(0),
    "spent_no": Decimal(0),
    "last_minute": -1,
    "last_20s_ts": 0,
    "last_winner": "None",
    "sell_all_price": Decimal(1),
    "can_trade": True,
    "liquidated": False,
    "num_flips": 0,
    "num_limit_orders": 0,
    "num_market_orders": 0,
    "num_orders": 0
})

client = ClobClient("https://clob.polymarket.com")  
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
FUNDER = "..."
PRIVATE_KEY = "..."
SIGNATURE_TYPE = 2
POLYGON_RPC = "https://polygon-rpc.com/"
POSITIONS_API = "https://data-api.polymarket.com/positions"
TS_SCRIPT_PATH = "/home/ubuntu/PolyBot/redeem.ts"
COMMAND = ["ts-node", TS_SCRIPT_PATH]

client = ClobClient(
    host=HOST,
    chain_id=CHAIN_ID,       
    key=PRIVATE_KEY,
    signature_type=SIGNATURE_TYPE,
    funder=FUNDER
)

def derive_API_creds():
    try:
        derived_creds = client.create_or_derive_api_creds()
        client.set_api_creds(derived_creds)
        print("✅ Successfully authenticated and set derived API credentials. Keys are valid.")
        return True
    except Exception as e:
        print(f"❌ AUTHENTICATION FAILED. Error: {e}")
        exit(1)

derive_API_creds()

def fetch_batch(offset, batch_size=500):
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": batch_size,
        "offset": offset,
        "closed": "false",
        "sortBy": "volume",
        "direction": "desc",
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        return data.get("markets", [])
    elif isinstance(data, list):
        return data
    return []

def safe_api_call(func, *args, retries=3, delay=3, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except PolyException as e:
            err = str(e).lower()
            if "502" in err or "bad gateway" in err or "connection" in err or "timeout" in err or "rate limit" in err:
                time.sleep(delay)
                continue
            elif "not enough funds" in err:
                return None
            else:
                return None
        except Exception:
            time.sleep(delay)
            continue
    return None

def get_all_markets(max_markets=20000, batch_size=500, max_workers=10):
    offsets = list(range(0, max_markets, batch_size))
    all_markets = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_batch, offset, batch_size) for offset in offsets]
        for future in as_completed(futures):
            try:
                batch = future.result()
                all_markets.extend(batch)
            except Exception:
                continue
    return all_markets

def filter_markets(all_markets):
    global current_markets
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(minutes=15)
    for m in all_markets:
        clob_ids_str = m.get("clobTokenIds", "[]")
        clob_ids = json.loads(clob_ids_str)
        try:
            if not m.get("active", False):
                continue
            end_str = m.get("endDate")
            if not end_str:
                continue
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            if now <= end_dt <= threshold:
                events = m.get("events", [])
                text_fields = " ".join([e.get("slug", "") for e in events]).lower()
                if MARKET in text_fields and TIMEFRAME in text_fields:
                    current_markets.append({
                        "question": m.get("question"),
                        "condition_id": m.get("conditionId"),
                        "direction": "up",
                        "token_id": clob_ids[0]
                    })
                    current_markets.append({
                        "question": m.get("question"),
                        "condition_id": m.get("conditionId"),
                        "direction": "down",
                        "token_id": clob_ids[1]
                    })
        except Exception:
            continue

def fetch_order_books_simple(filtered_markets):
    final_markets = []
    global markets_final
    for m in filtered_markets:
        try:
            token_id = m.get("token_id")
            if not token_id:
                continue
            try:
                book = client.get_order_book(token_id)
            except Exception:
                continue
            bids = getattr(book, "bids", [])
            asks = getattr(book, "asks", [])
            top_bid = Decimal(sorted((b.price for b in bids), reverse=True)[0]) if bids else Decimal(0)
            top_ask = Decimal(sorted((a.price for a in asks))[0]) if asks else Decimal(1)
            minTick = Decimal(m.get("min_tick", 0.01))
            info = {
                **m,
                "top_bid": [top_bid],
                "top_ask": [top_ask],
                "token_id": token_id,
                "condition_id": m.get("condition_id"),
                "min_tick": minTick,
                "direction": m.get("direction")
            }
            markets_final.append(info)
        except Exception:
            continue
    return markets_final

def delete_current_order(og_size=0):
    global tracked_buy_orders
    if tracked_buy_orders:
        price = Decimal(tracked_buy_orders[0].get("price") or 0)
        filled_size = Decimal(tracked_buy_orders[0].get("matched_size") or 0)
        if Decimal(og_size) != Decimal("0"):
            filled_size = og_size
        direction = tracked_buy_orders[0].get("direction")
        if direction == "YES":
            s_filled["yes_shares"] += filled_size
            s_filled["spent_yes"] += filled_size * price
        elif direction == "NO":
            s_filled["no_shares"] += filled_size
            s_filled["spent_no"] += filled_size * price
        s["yes_shares"] = s_filled["yes_shares"]
        s["spent_yes"] = s_filled["spent_yes"]
        s["no_shares"] = s_filled["no_shares"]
        s["spent_no"] = s_filled["spent_no"]
        tracked_buy_orders.clear()

def initialize_open_orders():
    global buy_order_markets
    global tracked_buy_orders
    buy_order_markets.clear()
    sell_order_markets.clear()
    all_historical_orders = []
    if tracked_buy_orders:
        try:
            all_historical_orders = client.get_orders(OpenOrderParams())
            OPEN_STATUSES = ["PENDING", "OPEN", "PENDING_PARTIAL_FILLED", "PARTIAL_FILLED", "LIVE"]
            open_buy_orders = [o for o in all_historical_orders if isinstance(o, dict) and o.get('side') == "BUY"]
        except Exception:
            return
        if not open_buy_orders:
            delete_current_order(Decimal(tracked_buy_orders[0].get("original_size")))
        for order in open_buy_orders:
            orderID = order.get("id")
            if orderID == tracked_buy_orders[0].get("order_id"):
                tokenID = order.get("asset_id")
                price = Decimal(order.get('price', 0.0))
                ogSize = Decimal(order.get("original_size"))
                matchedSize = Decimal(order.get("size_matched"))
                remainingSize = Decimal(ogSize - matchedSize)
                if remainingSize <= Decimal("0.01"):
                    delete_current_order()
                else:
                    tracked_buy_orders[0]["price"] = price
                    tracked_buy_orders[0]["original_size"] = ogSize
                    tracked_buy_orders[0]["matched_size"] = matchedSize
                    tracked_buy_orders[0]["remaining_size"] = remainingSize
                return True
        return True

def initialize_positions():
    wallet_address = FUNDER
    url = "https://data-api.polymarket.com/positions"
    offset = 0
    limit = 500
    global price_payed
    global buy_order_markets
    global sell_order_markets
    price_payed = Decimal(0.0)
    current_pnl = Decimal(0.0)
    num_positions = 0
    while True:
        params = {"user": wallet_address, "limit": limit, "offset": offset, "sizeThreshold": 0}
        r = safe_api_call(requests.get, url, params=params)
        r.raise_for_status()
        positions = r.json()
        if not positions:
            break
        for p in positions:
            if Decimal(p.get("size")) > Decimal("0.5"):
                num_positions += 1
                token_id = p.get("asset")
                current_positions.append({
                    "condition_id": p.get("conditionId"),
                    "token_id": token_id, 
                    "avgEntryPrice": p.get("avgPrice"),
                    "size": Decimal(p.get("size"))
                })
        offset += limit
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
    balance_and_allowance = client.get_balance_allowance(params=params) 
    balance = Decimal(balance_and_allowance.get('balance')) / Decimal(1000000)

def _get_mid_price(mkt):
    try:
        top_bid = Decimal(mkt.get("top_bid", [0])[0])
        top_ask = Decimal(mkt.get("top_ask", [1])[0])
        if top_bid >= Decimal("0.99"):
            return top_bid
        if top_bid > Decimal("0") and top_ask < Decimal("1"):
            return (top_bid + top_ask) / Decimal(2)
        if top_bid > Decimal("0"):
            return top_bid
        return top_ask
    except Exception:
        return Decimal(0)

def place_order(market, token_id, price, size, side, direction, add=False, expiration=0):
    try:
        order_args = OrderArgs(side=side, token_id=token_id, price=Decimal(price), size=Decimal(size))
        signed_order = client.create_order(order_args)  
        resp = client.post_order(signed_order, orderType=OrderType.GTC)
        if side == "SELL":
            delete_current_order()
            tracked_sell_orders.append(resp.get("orderID"))
            return True
        if side == "BUY":
            delete_current_order()
            tracked_buy_orders.append({
                "order_id": resp.get("orderID"),
                "condition_id": market.get("condition_id"),
                "token_id": token_id, 
                "price": Decimal(price),
                "original_size": Decimal(size),
                "matched_size": 0,
                "remaining_size": 0,
                "direction": direction
            })
            if add:
                all_placed_buy_orders.append(resp.get("orderID"))
            return True
    except PolyException as e:
        return False

def market_order(market, token_id, price, sizeShares, side, direction):
    sizeShares = Decimal(sizeShares)
    buy_price = Decimal(price)
    size = sizeShares.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    price_order = Decimal("0.02")
    if side == "BUY":
        size = (sizeShares * buy_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        price_order = Decimal("0.98")
        if size < 1.0:
            size = Decimal("1.01")
    actual_spend = (sizeShares * buy_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    try:
        client.cancel_all()
        order_args = MarketOrderArgs(side=side, price=price_order, token_id=token_id, amount=size)
        order_args.size = size
        order_args.expiration = 0
        signed_order = client.create_market_order(order_args)  
        resp = client.post_order(signed_order, orderType=OrderType.FOK)
        if side == "BUY":
            delete_current_order()
            tracked_buy_orders.append({
                "order_id": resp.get("orderID"),
                "condition_id": market.get("condition_id"),
                "token_id": token_id, 
                "price": (Decimal(price) + Decimal("0.02")),
                "original_size": Decimal(sizeShares),
                "matched_size": 0,
                "remaining_size": 0,
                "direction": direction
            })
        return True
    except PolyException as e:
        return False

def get_flip_size(num_loss, avg_loss, num_win, avg_win, price_win):
    x = sp.symbols('x')
    num_loss_eq = sp.Float(num_loss)
    avg_loss_eq = sp.Float(avg_loss)
    num_win_eq = sp.Float(num_win)
    avg_win_eq = sp.Float(avg_win)
    price_win_eq = sp.Float(price_win)
    profit = sp.Float("0.5")
    equation = num_loss_eq*avg_loss_eq + (num_win_eq + x)*((avg_win_eq*num_win_eq + price_win_eq*x)/(num_win_eq + x)) - (num_win_eq + x - profit)
    solution = str(float(sp.solve(equation, x)[0]))
    sol = Decimal(solution) * Decimal("1.8")
    if Decimal(sol) < Decimal("1"):
        return Decimal("0")
    if Decimal(sol) < Decimal("5.0"):
        return Decimal("5.0")
    return Decimal(sol)

def predict_next_flip(s, winner):
    spent_yes = Decimal(s["spent_yes"])
    spent_no = Decimal(s["spent_no"])
    yes_shares = Decimal(s["yes_shares"])
    no_shares = Decimal(s["no_shares"])
    avg_yes = spent_yes / yes_shares
    avg_no = spent_no / no_shares
    sol = 0
    if winner == "YES":
        sol = get_flip_size(yes_shares, avg_yes, no_shares, avg_no, Decimal("0.65"))
    else:
        sol = get_flip_size(no_shares, avg_no, yes_shares, avg_yes, Decimal("0.65"))
    return Decimal(sol)

def get_break_even_price(s, winner):
    spent_yes = Decimal(s["spent_yes"])
    spent_no = Decimal(s["spent_no"])
    yes_shares = Decimal(s["yes_shares"])
    no_shares = Decimal(s["no_shares"])
    avg_yes = spent_yes / yes_shares
    avg_no = spent_no / no_shares
    spent_total = yes_shares * avg_yes + no_shares * avg_no

    if winner == "YES":
        num = spent_total - no_shares
        den = yes_shares - no_shares
        if den == 0:
            return Decimal("0.5")
        return Decimal(num/den)
    else:
        num = spent_total - yes_shares
        den = no_shares - yes_shares
        if den == 0:
            return Decimal("0.5")
        return Decimal(num/den)

def liquidate_position(s, winner, price_yes, price_no):
    yes_shares = Decimal(s["yes_shares"])
    no_shares = Decimal(s["no_shares"])
    if winner == "YES":
        win_shares = yes_shares
        lose_shares = no_shares
        win_price = Decimal(price_yes)
        lose_price = Decimal(price_no)
    else:
        win_shares = no_shares
        lose_shares = yes_shares
        win_price = Decimal(price_no)
        lose_price = Decimal(price_yes)

    total_target_cash = win_shares * win_price + lose_shares * lose_price
    h_win = total_target_cash - win_shares
    h_lose = total_target_cash - lose_shares
    return h_win, h_lose

def calculate_price_market(s_filled, winner):
    if winner == "YES":
        num_win = Decimal(s_filled["yes_shares"])
        avg_win = Decimal(s_filled["spent_yes"]) / num_win
        num_loss = Decimal(s_filled["no_shares"])
        avg_loss = Decimal("0")
        if num_loss > Decimal("0"):
            avg_loss = Decimal(s_filled["spent_no"]) / num_loss
        to_buy = Decimal(num_win - num_loss)
    elif winner == "NO":
        num_win = Decimal(s_filled["no_shares"])
        avg_win = Decimal(s_filled["spent_no"]) / num_win
        num_loss = Decimal(s_filled["yes_shares"])
        avg_loss = Decimal("0")
        if num_loss > Decimal("0"):
            avg_loss = Decimal(s_filled["spent_yes"]) / num_loss
        to_buy = Decimal(num_win - num_loss)

    price = ((Decimal("0.98") - Decimal(str(avg_win))) * (Decimal(str(num_loss)) + Decimal(str(to_buy))) - Decimal(str(num_loss)) * Decimal(str(avg_loss))) / Decimal(str(to_buy))
    if price <= Decimal("0.01"):
        price = Decimal("0.011")
    if price >= Decimal("0.99"):
        price = Decimal("0.989")
    return Decimal(price), to_buy

def trade_market(market):
    global STRAT_STATE
    global STRAT_FILLED
    global upSize
    global downSize
    global tracked_buy_orders

    try:
        token_id = market.get("token_id")
        condition_id = market.get("condition_id")
        direction = market.get("direction", "up")
        my_mkt = next((m for m in markets_final if m.get("token_id") == token_id), None)
        opp_mkt = next((m for m in markets_final if m.get("condition_id") == condition_id and m.get("token_id") != token_id), None)
        if my_mkt is None or opp_mkt is None:
            return

        my_price = _get_mid_price(my_mkt)
        opp_price = _get_mid_price(opp_mkt)
        now = datetime.now(timezone.utc)
        minute_index = now.minute % 15
        second_index = now.second

        yes_mkt = my_mkt if my_mkt.get("direction") == "up" else (opp_mkt if opp_mkt.get("direction") == "up" else None)
        no_mkt  = my_mkt if my_mkt.get("direction") == "down" else (opp_mkt if opp_mkt.get("direction") == "down" else None)
        if yes_mkt is None or no_mkt is None:
            yes_mkt = next((x for x in (my_mkt, opp_mkt) if x.get("direction") == "up"), my_mkt)
            no_mkt = next((x for x in (my_mkt, opp_mkt) if x.get("direction") == "down"), opp_mkt)

        yes_price = _get_mid_price(yes_mkt)
        no_price = _get_mid_price(no_mkt)
        yes_token = yes_mkt.get("token_id")
        no_token = no_mkt.get("token_id")

        s_prev_winner = s.get("last_winner")
        winner = s_prev_winner
        if Decimal(yes_price) > Decimal("0.64"):
            winner = "YES"
        elif Decimal(no_price) > Decimal("0.64"):
            winner = "NO"

        total_spent = Decimal(Decimal(s["spent_yes"]) + Decimal(s["spent_no"]))
        if total_spent > Decimal(MAX_SPENT_SECURITY):
            yes_to_sell = Decimal(s["yes_shares"]) * Decimal("0.2")
            no_to_sell = Decimal(s["no_shares"]) * Decimal("0.2") 
            market_order(market, yes_token, Decimal(yes_price), yes_to_sell, "SELL", "YES") 
            market_order(market, no_token, Decimal(no_price), no_to_sell, "SELL", "NO")
            s["yes_shares"] -= Decimal(yes_to_sell)
            s["spent_yes"] -= (Decimal(yes_to_sell) * Decimal(yes_price))
            s["no_shares"] -= Decimal(no_to_sell)
            s["spent_no"] -= (Decimal(no_to_sell) * Decimal(no_price))

        num_flips = s["num_flips"]
        if minute_index <= 18 and s_prev_winner and (winner != s_prev_winner) and s["can_trade"] == True and abs(Decimal(s_filled["yes_shares"]) - Decimal(s_filled["no_shares"])) > Decimal("0.3"):
            if winner == "YES" and s.get("no_shares", 0) > 0:
                target_shares = Decimal(get_flip_size(Decimal(s_filled["no_shares"]), Decimal(s_filled["spent_no"]) / max(Decimal("1"), Decimal(s_filled["no_shares"])), Decimal(s_filled["yes_shares"]), Decimal(s_filled["spent_yes"]) / max(Decimal("1"), Decimal(s_filled["yes_shares"])), Decimal(yes_mkt.get("top_ask", [1])[0]) + Decimal("0.03")))
                if target_shares > Decimal("0") and Decimal(yes_mkt.get("top_ask", [1])[0]) < Decimal("0.99"):
                    market_order(market, yes_token, Decimal(yes_mkt.get("top_ask", [1])[0]) + Decimal("0.03"), target_shares, "BUY", "YES")
                    s["num_flips"] += 1
                    s["yes_shares"] += target_shares
                    s["spent_yes"] += target_shares * (Decimal(yes_mkt.get("top_ask", [1])[0]) + Decimal("0.03"))
            elif winner == "NO" and s.get("yes_shares", 0) > 0:
                target_shares = Decimal(get_flip_size(Decimal(s_filled["yes_shares"]), Decimal(s_filled["spent_yes"]) / max(Decimal("1"), Decimal(s_filled["yes_shares"])), Decimal(s_filled["no_shares"]), Decimal(s_filled["spent_no"]) / max(Decimal("1"), Decimal(s_filled["no_shares"])), Decimal(no_mkt.get("top_ask", [1])[0]) + Decimal("0.03")))
                if target_shares > Decimal("0") and Decimal(no_mkt.get("top_ask", [1])[0]) < Decimal("0.99"):
                    market_order(market, no_token, Decimal(no_mkt.get("top_ask", [1])[0]) + Decimal("0.03"), target_shares, "BUY", "NO")
                    s["num_flips"] += 1
                    s["no_shares"] += target_shares
                    s["spent_no"] += target_shares * (Decimal(no_mkt.get("top_ask", [1])[0]) + Decimal("0.03"))

        s["last_winner"] = winner

        if s["num_flips"] >= 2:
            next_flip_spent = Decimal(predict_next_flip(s, winner))
            total_spent_flip = Decimal(s_filled["spent_yes"]) + Decimal(s_filled["spent_no"]) + next_flip_spent
            if total_spent_flip > SPENT_LEVEL_3 or s["num_flips"] > 9:
                s["sell_all_price"] = Decimal("0.10")
                s["can_trade"] = False
            elif total_spent_flip > SPENT_LEVEL_2 or s["num_flips"] > 7:
                pass
            elif total_spent_flip > SPENT_LEVEL_1 or s["num_flips"] > 5:
                price = Decimal(get_break_even_price(s, winner))

    except Exception as e:
        print(f"⚠️ Error in trade_market: {e}")
        return

def time_remove_orders():
    global all_placed_buy_orders
    global tracked_buy_orders
    now = datetime.now(timezone.utc)
    minutes = now.minute
    seconds = now.second
    quarters = [11, 26, 41, 56]
    if len(tracked_buy_orders) != 0:
        for q in quarters:
            if minutes == q and 5 <= seconds <= 10:
                for order in all_placed_buy_orders:
                    if order == tracked_buy_orders[0].get("order_id"):
                        delete_current_order()
                        client.cancel_all()

def is_just_past_quarter(threshold_seconds=10):
    now = datetime.now(timezone.utc)
    minutes = now.minute
    seconds = now.second
    quarters = [0, 15, 30, 45]
    for q in quarters:
        if minutes == q and 0 <= seconds <= threshold_seconds:
            return True
    return False

def find_markets():
    current_markets.clear()
    all_markets = get_all_markets()
    filter_markets(all_markets)

def redeem_markets():
    try:
        result = subprocess.run(COMMAND, check=True, capture_output=True, text=True, shell=False)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None
    except FileNotFoundError:
        print("ts-node not found")
        return None

def get_allowance():
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
    balance_and_allowance = client.get_balance_allowance(params=params)
    balance = Decimal(balance_and_allowance.get('balance')) / Decimal(1000000)
    print(f"Balance: {balance} USDC.e")
    return balance

def Main():
    global lowest_bid_placed
    global upSize
    global downSize
    global s
    global s_filled
    tracked_buy_orders.clear()
    find_markets()
    reset = True
    trade = Decimal(get_allowance()) > Decimal(MIN_TRADE_SIZE)
    while reset:
        try:
            if is_just_past_quarter():
                reset = False
                lowest_bid_placed = 0.05
                upSize = 999
                downSize = 999
                STRAT_STATE[""] = {"yes_shares": Decimal(0),"no_shares": Decimal(0),"spent_yes": Decimal(0),"spent_no": Decimal(0),"last_minute": -1,"last_20s_ts": 0,"last_winner": "None","sell_all_price": Decimal(1),"can_trade": True,"liquidated": False,"num_flips": 0,"num_limit_orders": 0,"num_market_orders": 0,"num_orders": 0}
                STRAT_FILLED[""] = {"yes_shares": Decimal(0),"no_shares": Decimal(0),"spent_yes": Decimal(0),"spent_no": Decimal(0),"last_minute": -1,"last_20s_ts": 0,"last_winner": "None","sell_all_price": Decimal(1),"can_trade": True,"liquidated": False,"num_flips": 0,"num_limit_orders": 0,"num_market_orders": 0,"num_orders": 0}
                s = STRAT_STATE[""]
                s_filled = STRAT_FILLED[""]
                tracked_buy_orders.clear()
                threading.Thread(target=redeem_markets, daemon=True).start()
                time.sleep(20)
                break
            if trade:
                fetch_order_books_simple(current_markets)
                trade_market(current_markets[0])
                time.sleep(0.5)
                initialize_open_orders()
                time_remove_orders()
            else:
                threading.Thread(target=redeem_markets, daemon=True).start()
                time.sleep(20)
                trade = Decimal(get_allowance()) > Decimal(MIN_TRADE_SIZE)
            markets_final.clear()
            buy_order_markets.clear()
            sell_order_markets.clear()
            current_positions.clear()
        except Exception as e:
            print(f"💥 Fatal loop error: {e}")
            time.sleep(30)
            continue
Main()

