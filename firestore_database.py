from google.cloud import firestore
import datetime
from typing import Dict, Optional
import time
import os
from dotenv import load_dotenv

load_dotenv()
project_id = os.getenv("PROJECT_ID")

db = firestore.Client(
    project = project_id,
    database = project_id
)

#######################################################
# CORE FIRESTORE DATA STRUCTURES
#######################################################

def create_user_if_not_exists(user_id: str, email: str) -> Dict:
    """
    Ensures a user document with userId=user_id in 'users' collection.
    Returns the doc data.
    """
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        new_data = {
            "userId": user_id,
            "email": email,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(new_data)
        return new_data

def create_trade_record(
    user_id: str,
    ticker: str,
    position_type: str,
    num_shares: int,
    entry_date: Optional[str],
    entry_price: float,
    opened_by_user: bool,
    opened_by_model: bool,
    status: str = "open",
    pending_open: bool = False,
    pending_open_date: Optional[str] = None
) -> str:
    """
    Creates a new Firestore doc in 'trades' collection, storing all necessary fields.
    Returns the newly created doc ID.
    """
    trade_doc = {
        "userId": user_id,
        "ticker": ticker,
        "positionType": position_type,      # "long" or "short"
        "numShares": num_shares,
        "entryDate": entry_date,            # string or None
        "entryPrice": entry_price,          # 0.0 if not opened yet
        "status": status,                   # "open", "scheduled", or "closed"
        "opened_by_user": opened_by_user,
        "opened_by_model": opened_by_model,
        "pending_open": pending_open,
        "pending_open_date": pending_open_date,
        "closeDate": None,
        "closePrice": None,
        "pnl_usd": None,
        "return_pct": None,
        "createdAt": firestore.SERVER_TIMESTAMP
    }
    doc_ref = db.collection("trades").add(trade_doc)
    return doc_ref[1].id if len(doc_ref) > 1 else doc_ref[0].id

def schedule_trade_record(
    user_id: str,
    ticker: str,
    position_type: str,
    num_shares: int,
    scheduled_date: str,
    opened_by_user: bool,
    opened_by_model: bool
) -> str:
    """
    Creates a 'scheduled' trade doc that hasn't assigned entry_price or entry_date yet.
    """
    trade_doc = {
        "userId": user_id,
        "ticker": ticker,
        "positionType": position_type,
        "numShares": num_shares,
        "entryDate": None,      # not opened
        "entryPrice": 0.0,
        "status": "scheduled",
        "opened_by_user": opened_by_user,
        "opened_by_model": opened_by_model,
        "pending_open": True,
        "pending_open_date": scheduled_date,
        "closeDate": None,
        "closePrice": None,
        "pnl_usd": None,
        "return_pct": None,
        "createdAt": firestore.SERVER_TIMESTAMP
    }
    doc_ref = db.collection("trades").add(trade_doc)
    return doc_ref[1].id if len(doc_ref) > 1 else doc_ref[0].id

def auto_open_scheduled_trades():
    """
    Queries all trades with pending_open=True and status='scheduled'.
    If the scheduled_date <= today, finalize them by fetching a historical close price
    (or using today's close) and setting status='open', entry_price, entry_date, etc.
    """
    today = datetime.date.today()
    trades_ref = db.collection("trades").where("pending_open", "==", True).where("status", "==", "scheduled")
    docs = trades_ref.stream()

    changed = False
    for doc in docs:
        data = doc.to_dict()
        sched_date_str = data.get("pending_open_date")
        if not sched_date_str:
            continue
        sched_date = datetime.date.fromisoformat(sched_date_str)

        if sched_date <= today:
            # We can finalize. Let's do a get_historical_close_on_or_before if you want historical logic
            # For simplicity, we do a "today's close" approach. Adapt as needed.
            from market_data import get_historical_close_on_or_before
            try:
                close_price, actual_date_used = get_historical_close_on_or_before(data["ticker"], sched_date)
            except ValueError:
                # No data found => skip
                continue

            # If found a price, finalize
            trade_id = doc.id
            update_data = {
                "pending_open": False,
                "pending_open_date": None,
                "entryPrice": close_price,
                "entryDate": actual_date_used.strftime("%Y-%m-%d"),
                "status": "open"
            }
            db.collection("trades").document(trade_id).update(update_data)
            changed = True

    return changed

def close_trade_in_firestore(trade_id: str, close_price: float, close_date: str):
    """
    Closes the specified trade doc in Firestore. Computes PnL, return_pct, etc.
    """
    doc_ref = db.collection("trades").document(trade_id)
    snap = doc_ref.get()
    if not snap.exists:
        raise ValueError("Trade not found in Firestore.")

    data = snap.to_dict()
    if data["status"] == "closed":
        raise ValueError("Trade is already closed.")

    entry_p = data["entryPrice"]
    shares = data["numShares"]
    pos_type = data["positionType"]

    if pos_type == "long":
        pnl_usd = (close_price - entry_p) * shares
    else:
        # short
        pnl_usd = (entry_p - close_price) * shares

    if entry_p > 0 and shares > 0:
        return_pct = (pnl_usd / (entry_p * shares)) * 100
    else:
        return_pct = 0

    update_data = {
        "closeDate": close_date,
        "closePrice": round(close_price, 2),
        "pnl_usd": round(pnl_usd, 2),
        "return_pct": round(return_pct, 2),
        "status": "closed"
    }
    doc_ref.update(update_data)

def update_unrealized_pnl():
    """
    On every rerun, fetch the latest close for open trades, recalc unrealized PnL.
    """
    from market_data import get_latest_price
    open_query = db.collection("trades").where("status", "==", "open")
    docs = open_query.stream()

    for doc in docs:
        data = doc.to_dict()
        trade_id = doc.id
        ticker = data["ticker"]
        pos_type = data["positionType"]
        entry_p = data["entryPrice"]
        shares = data["numShares"]

        # if we can't fetch, default to entry
        try:
            current_price = get_latest_price(ticker)
        except:
            current_price = entry_p

        if pos_type == "long":
            unrealized_usd = (current_price - entry_p) * shares
        else:
            unrealized_usd = (entry_p - current_price) * shares

        if entry_p > 0 and shares > 0:
            unrealized_pct = (unrealized_usd / (entry_p * shares)) * 100
        else:
            unrealized_pct = 0

        db.collection("trades").document(trade_id).update({
            "unrealized_pnl_usd": round(unrealized_usd, 2),
            "unrealized_return_pct": round(unrealized_pct, 2)
        })


#######################################################
# Querying trades for display
#######################################################
def get_user_open_positions(user_id: str) -> list:
    """
    Return open trades for the user.
    """
    q = db.collection("trades").where("userId", "==", user_id).where("status", "==", "open")
    docs = q.stream()
    results = []
    for d in docs:
        item = d.to_dict()
        item["trade_id"] = d.id
        results.append(item)
    return results

def get_user_closed_positions(user_id: str) -> list:
    """
    Return closed trades for the user.
    """
    q = db.collection("trades").where("userId", "==", user_id).where("status", "==", "closed")
    docs = q.stream()
    results = []
    for d in docs:
        item = d.to_dict()
        item["trade_id"] = d.id
        results.append(item)
    return results
