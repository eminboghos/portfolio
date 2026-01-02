import requests
import threading
import subprocess
from datetime import datetime, timedelta, timezone
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams, TradeParams, OpenOrderParams
from py_clob_client.clob_types import ApiCreds
from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions, OrderType, PostOrdersArgs, MarketOrderArgs
from py_clob_client.exceptions import PolyException
from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
from py_clob_client.exceptions import PolyException
from decimal import Decimal
import time
from datetime import datetime
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, ROUND_HALF_UP
import requests
from decimal import ROUND_DOWN  
import eth_account
from eth_account.messages import encode_defunct
from web3 import Web3
from eth_account import Account
import subprocess
from py_builder_relayer_client.client import RelayClient
from py_builder_signing_sdk.config import BuilderConfig, BuilderApiKeyCreds
import os
from eth_utils import to_bytes


MIN_VOLUME = 150
MIN_DAYS_TO_CLOSE = 2
MAX_DAYS_TO_CLOSE_SPORTS = 5
MAX_DAYS_FROM_OPEN = 4
MAX_BID = 0.06         
MIN_ASK_MULTIPLE = 2.5  
SPORT_MIN_ASK_MULTIPLE = 4
MIN_DAY_CHANGE = -0.004
MAX_PAYED_ORDERS = 750
POSITION_SIZE = 5


current_markets = []
markets_final = []
buy_order_markets = []
sell_order_markets = []
current_positions = []
current_buy_orders = []
lowest_bid_placed = 0.05
upSize = 999
downSize = 999
STRAT_STATE = {}


client = ClobClient("https://clob.polymarket.com")  # read-only client
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon chain ID
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
        print(f"❌ AUTHENTICATION FAILED. Review PRIVATE_KEY and FUNDER settings. Error: {e}")
        exit(1)

derive_API_creds()
#print(client.get_api_keys())

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
    else:
        return []
    
def safe_api_call(func, *args, retries=3, delay=3, **kwargs):
    """
    Calls a Polymarket API function safely with retry logic.
    Retries on temporary errors (502, connection reset, timeout, etc.).
    """
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except PolyException as e:
            err = str(e).lower()

            if "502" in err or "bad gateway" in err or "connection" in err or "timeout" in err or "rate limit" in err:
                print(f"⚠️ API/connection issue: {err}. Retrying ({attempt+1}/{retries})...")
                time.sleep(delay)
                continue
            elif "not enough funds" in err:
                print("⚠️ Not enough funds, skipping this order.")
                return None
            else:
                print(f"❌ Unhandled PolyException: {e}")
                return None

        except Exception as e:
            print(f"❌ Unknown error: {e}. Retrying ({attempt+1}/{retries})...")
            time.sleep(delay)
            continue

    print("🚫 API call failed after retries, skipping.")
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
                print(f"✅ Loaded {len(all_markets)} markets so far...")
            except Exception as e:
                print(f"⚠️ Error fetching batch: {e}")

    print(f"\nTotal markets fetched: {len(all_markets)}")
    return all_markets

    print(f"\nTotal markets fetched: {len(all_markets)}")
    return all_markets

def filter_markets(all_markets):
    global current_markets
    print(datetime.utcnow())
    for m in all_markets:
        clob_ids_str = m.get("clobTokenIds", "[]")
        clob_ids = json.loads(clob_ids_str)
        try:
            if not m.get("active", False):
                continue
            
            events = m.get("events", [])
            text_fields = " ".join([e.get("slug", "") for e in events]).lower()
        
            now = datetime.now(timezone.utc)  
            threshold = now + timedelta(minutes=15)

            end_str = m.get("endDate")
            if not end_str:
                continue
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        
            if now <= end_dt <= threshold:
                events = m.get("events", [])
                text_fields = " ".join([e.get("slug", "") for e in events]).lower()
                if "btc" in text_fields and "15m" in text_fields:
                    print("✅ Bitcoin 15-min market ending soon found:")
                    print("Question:", m.get("question"))
                    print("End date:", m.get("endDate"))
                    print("Best bid:", m.get("bestBid"))
                    current_markets.append({
                        "question": m.get("question"),
                        "condition_id":m.get("conditionId"),
                        "direction": "up",
                        "token_id": clob_ids[0]
                    })
                    current_markets.append({
                        "question": m.get("question"),
                        "condition_id":m.get("conditionId"),
                        "direction": "down",
                        "token_id": clob_ids[1]
                    })
  
        except Exception as e:
            print(f"⚠️ Skipping market due to error: {e}")
            continue

def fetch_order_books_simple(filtered_markets):
    final_markets = []
    global current_markets
    global markets_final
    for m in filtered_markets:
        try:
            token_id = m.get("token_id")
            if not token_id:
                continue
            try:
                book=client.get_order_book(token_id)
            except PolyException as e:
                print(f"❌ CLOB API FAILED. Error: {e}")
                return []
            except Exception as e:
                print(f"❌ Unexpected error in CLOB fetch: {e}")
                return []

            bids = getattr(book, "bids", [])
            asks = getattr(book, "asks", [])

            # Handle empty bids/asks
            top_bid = Decimal(0)
            top_ask = Decimal(0)
            no_bid = False
            no_ask = False

            if not bids:
                bids = [0.0]
                no_bid = True
            if not asks:
                asks = [1.0]
                no_ask = True

            # Compute top bid
            if not no_bid:
                sorted_bids = sorted((b.price for b in bids), reverse=True)
                top_bid = Decimal(sorted_bids[0])
                top_bid2 = Decimal(sorted_bids[1]) if len(sorted_bids) >= 2 else Decimal(0)
                top_bid_size = Decimal(next(b.size for b in bids if Decimal(b.price) == top_bid))
            else:
                sorted_bids = []
                top_bid2 = Decimal(0)
                top_bid_size = 0

            # Compute top ask
            if not no_ask:
                sorted_asks = sorted((a.price for a in asks))
                top_ask = Decimal(sorted_asks[0])
                top_ask2 = Decimal(sorted_asks[1]) if len(sorted_asks) >= 2 else Decimal(1)
                top_ask_size = Decimal(next(a.size for a in asks if Decimal(a.price) == top_ask))
            else:
                sorted_asks = []
                top_ask2 = Decimal(1)
                top_ask_size = 0

            minTick = Decimal(m.get("min_tick", 0.01))
            conditionID = m.get("condition_id")

            info = {
                **m,
                "top_bid": [top_bid, top_bid2],
                "top_bid_size": top_bid_size,
                "top_ask": [top_ask, top_ask2],
                "top_ask_size": top_ask_size,
                "token_id": token_id,
                "condition_id": conditionID,
                "sorted_bids": sorted_bids,
                "sorted_asks": sorted_asks,
                "bid_sizes": [b.size for b in bids] if not no_bid else [],
                "ask_sizes": [a.size for a in asks] if not no_ask else [],
                "min_tick": minTick,
                "direction": m.get("direction")
            }

            markets_final.append(info)


        except Exception as e:
            print(f"⚠️ Skipping market {m.get('condition_id')} due to error: {e}")
            continue

    return markets_final

def initialize_open_orders():
    """
    Fetches ALL historical orders and filters them locally using 
    DICTIONARY KEY ACCESS to handle the 'dict' object error.
    """
    global buy_order_markets
    buy_order_markets.clear()
    sell_order_markets.clear()
    print("\n--- Initializing Open Orders (Accessing Order Dictionaries) ---")
    for m in current_markets:
        try:
            print("🔍 Fetching all historical orders from the CLOB...")
            #all_historical_orders = client.get_orders()
            all_historical_orders = client.get_orders(OpenOrderParams(asset_id=m.get("token_id")))
            OPEN_STATUSES = ["PENDING", "OPEN", "PENDING_PARTIAL_FILLED", "PARTIAL_FILLED", "LIVE"]
            open_buy_orders = []
            open_sell_orders = []
            for order in all_historical_orders:
                if (isinstance(order, dict) and 
                    order.get('status') in OPEN_STATUSES and 
                    order.get('side') == "BUY"):
                    
                    open_buy_orders.append(order)
                if (isinstance(order, dict) and 
                    order.get('status') in OPEN_STATUSES and 
                    order.get('side') == "SELL"):
                    
                    open_sell_orders.append(order)
                
            all_buy_token_ids = []
            for order in open_buy_orders:
                orderID = order.get("id")
                conditionID = order.get("market")
                tokenID = order.get("asset_id")
                if (tokenID in all_buy_token_ids):
                    safe_api_call(client.cancel, orderID)  #changed api call here
                else:
                    all_buy_token_ids.append(tokenID)
                    price = Decimal(order.get('price', 0.0))
                    ogSize = Decimal(order.get("original_size"))
                    matchedSize = Decimal(order.get("size_matched"))
                    remainingSize = ogSize - matchedSize
                    buy_order_markets.append({
                        "order_id": orderID,
                        "condition_id": conditionID,
                        "token_id": tokenID, 
                        "price": price,
                        "original_size": ogSize,
                        "matched_size": matchedSize,
                        "remaining_size": remainingSize
                    })
            
            for order in open_sell_orders:
                
                orderID = order.get("id")
                conditionID = order.get("market")
                tokenID = order.get("asset_id")
                price = Decimal(order.get('price', 0.0))
                ogSize = Decimal(order.get("original_size"))
                matchedSize = Decimal(order.get("size_matched"))
                remainingSize = ogSize - matchedSize
                sell_order_markets.append({
                    "order_id": orderID,
                    "condition_id": conditionID,
                    "token_id": tokenID, 
                    "price": price,
                    "original_size": ogSize,
                    "matched_size": matchedSize,
                    "remaining_size": remainingSize
                })
        except Exception as e:
            print(f"❌ Critical Failure: Could not initialize open orders. Error: {e}")
            
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
        params = {
            "user": wallet_address,
            "limit": limit,  
            "offset": offset,
            "sizeThreshold": 0,  
        }
        # r = requests.get(url, params=params)
        r = safe_api_call(requests.get, url, params=params) 
        r.raise_for_status()
        positions = r.json()
        #print(positions)
        

        if not positions:
            break
        
        for p in positions:
            if (Decimal(p.get("size")) > 0.5):
                num_positions += 1
                if (True):
                    token_id = p.get("asset")
                    matching_buy_orders = [o for o in buy_order_markets if o["token_id"] == token_id]
                    matching_sell_orders = [o for o in sell_order_markets if o["token_id"] == token_id]
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

def is_near_quarter_hour(threshold_minutes=5):
    """
    Returns True if current UTC time is within `threshold_minutes`
    *before* 0, 15, 30, or 45 minute marks.
    """
    now = datetime.now(timezone.utc)
    minutes = now.minute
    seconds = now.second

    
    remainder = minutes % 15
    minutes_to_next_quarter = 15 - remainder - (seconds / 60)

    return 0 <= minutes_to_next_quarter <= threshold_minutes

def _get_mid_price(mkt):
    
    try:
        top_bid = Decimal(mkt.get("top_bid", [0])[0])
        top_ask = Decimal(mkt.get("top_ask", [1])[0])
        if top_bid >= 0.99:   
            return top_bid
        if top_bid > 0 and top_ask < 1:
            return (top_bid + top_ask) / Decimal(2)
        if top_bid > 0:
            return top_bid
        return top_ask
    except Exception:
        return Decimal(0)
    
def _dollars_to_shares(dollars, price):
    if price <= 0:
        return Decimal(0)
    return 5


def place_order(market, token_id, price, size, side):
    try:
        order_args = OrderArgs(
            side=side,
            token_id=token_id,
            price=Decimal(price),
            size=Decimal(size)
        )
        signed_order = client.create_order(order_args)  
        #new_orders_to_post.append(PostOrdersArgs(order=signed_order, orderType=OrderType.GTC)) 
        resp = client.post_order(signed_order, orderType=OrderType.GTC)
        if (side == "SELL"):
            print(f"✅ Sell order on {market.get('question', '')}: {Decimal(size)} shares at {price}")
            return True
        if (side == "BUY"):
            print(f"✅ Buy order on {market.get('question', '')}: {Decimal(size)} shares at {price}")
            return True

    except PolyException as e:
        if "not enough funds" in str(e).lower():
            print("⚠️ Retrying after balance update...")
        else:
            raise e
        return False
    
def market_order(market, token_id, price, sizeShares, side):
    

    sizeShares = Decimal(sizeShares)
    buy_price = Decimal(price)
    size = sizeShares.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    price_order = Decimal("0.02")
    if (side == "BUY"):
        size = (sizeShares * buy_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        price_order = Decimal("0.98")

    
    actual_spend = (size * buy_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    print(f"BUY size: {size}, total cost: {actual_spend}")

    try:
        order_args = MarketOrderArgs(
            side=side,
            price=price_order,
            token_id=token_id,
            amount=size
        )
        order_args.size = size
        order_args.expiration = 0
        signed_order = client.create_market_order(order_args)  
        #new_orders_to_post.append(PostOrdersArgs(order=signed_order, orderType=OrderType.GTC)) 
        resp = client.post_order(signed_order, orderType=OrderType.FOK)
        print(f"✅ {side} market order on {market.get('question', '')}: {Decimal(size)} shares.")
        return True

    except PolyException as e:
        if "not enough funds" in str(e).lower():
            print("⚠️ Retrying after balance update...")
        else:
            raise e
        return False
    
def get_sell_price(avg_price):
    if (avg_price > 0.045):
        return 0.06
    if (avg_price > 0.035):
        return 0.05
    if (avg_price > 0.025):
        return 0.04
    if (avg_price > 0.016):
        return 0.03
    if (avg_price > 0.007):
        return 0.02
    return 1

    
def get_buy_size(price):
    if (price >= 0.049):
        return POSITION_SIZE
    if (price >= 0.039):
        return POSITION_SIZE * 3
    if (price >= 0.029):
        return POSITION_SIZE * 6
    if (price >= 0.019):
        return POSITION_SIZE * 11
    if (price >= 0.009):
        return POSITION_SIZE * 20
    return 0



def trade_market(market):

    global STRAT_STATE
    global upSize
    global downSize

    try:
        token_id = market.get("token_id")
        condition_id = market.get("condition_id")
        direction = market.get("direction", "up") 
        # find the opposite-side market info from markets_final
        my_mkt = next((m for m in markets_final if m.get("token_id") == token_id), None)
        opp_mkt = next((m for m in markets_final if m.get("condition_id") == condition_id and m.get("token_id") != token_id), None)

        if my_mkt is None or opp_mkt is None:
            return  # can't operate without both sides

        
        my_price = _get_mid_price(my_mkt)
        opp_price = _get_mid_price(opp_mkt)

        
        now = datetime.now(timezone.utc)
        minute_index = now.minute % 15
        second_index = now.second
        second = now.second

        
        s = STRAT_STATE.setdefault(condition_id, {
            "yes_shares": Decimal(0),
            "no_shares": Decimal(0),
            "spent_yes": Decimal(0),
            "spent_no": Decimal(0),
            "last_minute": -1,
            "last_20s_ts": 0,
            "last_winner": None
        })

        yes_mkt = my_mkt if my_mkt.get("direction") == "up" else (opp_mkt if opp_mkt.get("direction") == "up" else None)
        no_mkt  = my_mkt if my_mkt.get("direction") == "down" else (opp_mkt if opp_mkt.get("direction") == "down" else None)
        if yes_mkt is None or no_mkt is None:
            yes_mkt = next((x for x in (my_mkt, opp_mkt) if x.get("direction") == "up"), my_mkt)
            no_mkt = next((x for x in (my_mkt, opp_mkt) if x.get("direction") == "down"), opp_mkt)

        yes_price = _get_mid_price(yes_mkt)
        print("YES : ", yes_price)
        no_price = _get_mid_price(no_mkt)
        print("NO : ", no_price)
        yes_token = yes_mkt.get("token_id")
        no_token = no_mkt.get("token_id")

        s_prev_winner = s.get("last_winner")
        winner = s_prev_winner
        if yes_price > Decimal("0.62"):
            winner = "YES"
        elif no_price > Decimal("0.62"):
            winner = "NO"

        total_spent = s["spent_yes"] + s["spent_no"]
        if total_spent > 400:
            yes_to_sell = Decimal(s["yes_shares"]) * Decimal("0.3")
            no_to_sell = Decimal(s["no_shares"]) * Decimal("0.3") 
            market_order(market, yes_token, Decimal(Decimal(yes_price)), yes_to_sell, "SELL") 
            market_order(market, no_token, Decimal(Decimal(no_price)), no_to_sell, "SELL")
            s["yes_shares"] -= Decimal(yes_to_sell)
            s["spent_yes"] -= (Decimal(yes_to_sell) * Decimal(yes_price))
            s["no_shares"] -= Decimal(no_to_sell)
            s["spent_no"] -= (Decimal(no_to_sell) * Decimal(no_price))


        

        # immediate flip handling:
        if s_prev_winner and (winner != s_prev_winner):
            if winner == "YES" and s.get("no_shares", 0) > 0:
                print("flip to YES")
                # buy NO shares equal to yes_shares at price 0.65 if possible
                target_shares = Decimal(s["no_shares"]) * Decimal("1.85") - Decimal(s["yes_shares"])
                size = target_shares
                if size > 0:
                    print("flip confirmed")
                    print(f"Flip detected {s_prev_winner}-> {winner} for condition {condition_id}: attempting immediate buy {size} NO at 0.65")
                    # place order on NO token
                    market_order(market, yes_token, Decimal(Decimal(yes_price) + Decimal("0.01")), size, "BUY")   
                    s["yes_shares"] += Decimal(size)
                    s["spent_yes"] += (Decimal(size) * Decimal(Decimal(yes_price) + Decimal("0.01")))

            elif winner == "NO" and s.get("yes_shares", 0) > 0:
                print("flip to NO")
                # buy YES equal to no_shares at 0.65
                target_shares = Decimal(s["yes_shares"]) * Decimal("1.85") - Decimal(s["no_shares"])
                size = target_shares
                if size > 0:
                    print("flip confirmed")
                    print(f"Flip detected {s_prev_winner}-> {winner} for condition {condition_id}: attempting immediate buy {size} YES at 0.65")
                    market_order(market, no_token, Decimal(Decimal(no_price) + Decimal("0.01")), size, "BUY")
                    s["no_shares"] += Decimal(size)
                    s["spent_no"] += (Decimal(size) * Decimal(Decimal(no_price) + Decimal("0.01")))

        # store new winner
        s["last_winner"] = winner

        if 3 <= minute_index <= 11:
            if s.get("last_minute") != minute_index:
                span = 8 
                pos = minute_index - 5
                if span <= 1:
                    dollar_amt = Decimal('1')
                else:
                    frac = Decimal(pos) / Decimal(span - 1)
                    dollar_amt = Decimal('1') + frac * (Decimal('3') - Decimal('1')) 
                if winner == "YES":
                    buy_token = yes_token
                    buy_price = yes_price
                    buy_side_label = "YES"
                else:
                    buy_token = no_token
                    buy_price = no_price
                    buy_side_label = "NO"

                if buy_price >= Decimal('0.65') and buy_price <= Decimal('0.94'):
                   
                    size = _dollars_to_shares(dollar_amt, buy_price if buy_price > 0 else Decimal('0.65'))
                    if size > 0:
                        print(f"[Minute buy] condition {condition_id}: minute {minute_index} buying {size} {buy_side_label} at price {buy_price} (target ${dollar_amt})")
                        # place limit buy at the current price to try and fill
                        place_order(market, buy_token, Decimal(Decimal(buy_price) + Decimal("0.01")), Decimal(size), "BUY")
                        # update state
                        if buy_side_label == "YES":
                            s["yes_shares"] += size
                            s["spent_yes"] += (size * buy_price)
                        else:
                            s["no_shares"] += size
                            s["spent_no"] += (size * buy_price)
                else:
                    print(f"[Minute buy] condition {condition_id}: winner {winner} price {buy_price} < 0.65, skipping minute buy")

                total_spent = s["spent_yes"] + s["spent_no"]
                desired_no_spent = (total_spent // Decimal('12')) * Decimal('1')
                if total_spent > 0:
                    desired_no_spent = ( (total_spent / Decimal('12')).to_integral_value(rounding=ROUND_DOWN) ) * Decimal('1')
                    if s["spent_no"] < desired_no_spent:
                        buy_at_price = (Decimal(no_price) - Decimal('0.01')) if (Decimal(no_price) - Decimal('0.01')) >= 0.011 else 0.011
                        size_short = 5
                        if size_short > 0:
                            print(f"[Allocation enforcement] Buying {size_short} NO to meet $1 per $5 rule ")
                            s["last_minute"] = minute_index
                            place_order(market, no_token, buy_at_price, size_short, "BUY")
                            s["no_shares"] += size_short
                            s["spent_no"] += (size_short * buy_at_price)
                    elif s["spent_yes"] < desired_no_spent:
                        buy_at_price = (Decimal(yes_price) - Decimal('0.01')) if (Decimal(yes_price) - Decimal('0.01')) >= 0.011 else 0.011# Decimal('0.65')
                        size_short = 5
                        if size_short > 0:
                            print(f"[Allocation enforcement] Buying {size_short} NO to meet $1 per $5 rule")
                            s["last_minute"] = minute_index
                            place_order(market, yes_token, buy_at_price, size_short, "BUY")
                            s["yes_shares"] += size_short
                            s["spent_yes"] += (size_short * buy_at_price)
                s["last_minute"] = minute_index

        elif minute_index >= 12: 
            now_ts = int(time.time())
            if now_ts - s.get("last_20s_ts", 0) >= 30:
                per_buy_dollars = Decimal('1')
                if yes_price < Decimal('0.93') and winner == "YES":
                    size = _dollars_to_shares(per_buy_dollars, yes_price)
                    if size > 0:
                        print(f"[20s buy] Buying {size} YES at {yes_price} (because <0.95)")
                        place_order(market, yes_token, yes_price, 5, "BUY")
                        s["yes_shares"] += size
                        s["spent_yes"] += (size * yes_price)
                if no_price < Decimal('0.93') and winner == "NO":
                    size = _dollars_to_shares(per_buy_dollars, no_price)
                    if size > 0:
                        print(f"[20s buy] Buying {size} NO at {no_price} (because <0.95)")
                        place_order(market, no_token, no_price, 5, "BUY")
                        s["no_shares"] += size
                        s["spent_no"] += (size * no_price)
                
                total_spent = s["spent_yes"] + s["spent_no"]
                desired_no_spent = (total_spent // Decimal('12')) * Decimal('1') 
                if total_spent > 0:
                    desired_no_spent = ( (total_spent / Decimal('12')).to_integral_value(rounding=ROUND_DOWN) ) * Decimal('1')
                    if s["spent_no"] < desired_no_spent:
                        buy_at_price = (Decimal(no_price) - Decimal('0.01')) if (Decimal(no_price) - Decimal('0.01')) >= 0.011 else 0.011
                        size_short = 5
                        if size_short > 0:
                            print(f"[Allocation enforcement] Buying {size_short} NO to meet $1 per $5 rule ")
                            s["last_20s_ts"] = now_ts
                            place_order(market, no_token, buy_at_price, size_short, "BUY")
                            s["no_shares"] += size_short
                            s["spent_no"] += (size_short * buy_at_price)
                    elif s["spent_yes"] < desired_no_spent:
                        buy_at_price = (Decimal(yes_price) - Decimal('0.01')) if (Decimal(yes_price) - Decimal('0.01')) >= 0.011 else 0.011
                        size_short = 5
                        if size_short > 0:
                            print(f"[Allocation enforcement] Buying {size_short} NO to meet $1 per $5 rule")
                            s["last_20s_ts"] = now_ts
                            place_order(market, yes_token, buy_at_price, size_short, "BUY")
                            s["yes_shares"] += size_short
                            s["spent_yes"] += (size_short * buy_at_price)
                s["last_20s_ts"] = now_ts

        elif yes_price > Decimal("0.65") and s["no_shares"] > s["yes_shares"]:
            diff = s["no_shares"] - s["yes_shares"]
            if diff > 0:
                print(f"[Rebalance after crash] Buying {diff} YES at 0.65 to make up difference")
                place_order(market, yes_token, Decimal(yes_price), diff, "BUY")
                s["yes_shares"] += diff
                s["spent_yes"] += (diff * Decimal(yes_price))

        elif no_price > Decimal("0.65") and s["yes_shares"] > s["no_shares"]:
            diff = s["yes_shares"] - s["no_shares"]
            if diff > 0:
                print(f"[Rebalance after crash] Buying {diff} NO at 0.65 to make up difference")
                place_order(market, no_token, Decimal(no_price), diff, "BUY")
                s["no_shares"] += diff
                s["spent_no"] += (diff * Decimal(no_price))

    except Exception as e:
        print(f"⚠️ Error in new trade_market strategy for market {market.get('condition_id')}: {e}")
        return
    

def is_just_past_quarter(threshold_seconds=25):
    """
    Returns True if current UTC time is within `threshold_seconds` of
    0:15, 15:15, 30:15, or 45:15.
    """
    now = datetime.now(timezone.utc)
    minutes = now.minute
    seconds = now.second

    quarters = [2, 17, 32, 47]
    for q in quarters:
        if minutes == q and 15 <= seconds <= threshold_seconds:
            return True
    return False

def find_markets():
    current_markets.clear()
    all_markets = get_all_markets()
    filter_markets(all_markets)

def redeem_markets():
    try:
        print(f"Executing command: {' '.join(COMMAND)}")

        result = subprocess.run(
            COMMAND,
            check=True,
            capture_output=True,
            text=True,
            shell=False 
        )

        print("\n--- TS Script Output (STDOUT) ---")
        print(result.stdout)
        
        if result.stderr:
            print("\n--- TS Script Errors (STDERR) ---")
            print(result.stderr)

        print(f"\nTS Script finished with return code: {result.returncode}")

        return result.stdout

    except subprocess.CalledProcessError as e:
        print("\n*** TS Script Execution Failed ***")
        print(f"Command: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        return None

    except FileNotFoundError:
        print("\n*** Execution Error ***")
        print("Error: The 'ts-node' command was not found.")
        print("Please ensure 'ts-node' is installed (npm install -g ts-node) or available in your environment PATH.")
        return None

def Main():
    global lowest_bid_placed
    global upSize
    global downSize
    global STRAT_STATE
    find_markets()
    reset = True
    time.sleep(1)
    while reset:
        try:
            if is_just_past_quarter():
                print("RRRRRRRRRRRRRRRRRRRRRRRRReset market")
                reset = False
                lowest_bid_placed = 0.05
                upSize = 999
                downSize = 999
                STRAT_STATE = {}
                threading.Thread(target=redeem_markets, daemon=True).start()
                time.sleep(15)
                break
            fetch_order_books_simple(current_markets)
            trade_market(current_markets[0])
            markets_final.clear()
            buy_order_markets.clear()
            sell_order_markets.clear()
            current_positions.clear()
            
            
        except Exception as e:
            print(f"💥 Fatal loop error: {e}")
            time.sleep(3)
            continue

        finally:
            print()
    Main()

Main()
