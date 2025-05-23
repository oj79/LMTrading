import streamlit as st
import uuid
from typing import List, Dict
from data_persistence import load_trades_data

def initialize_session_state():
    if "user_open_positions" not in st.session_state:
        data = load_trades_data()
        st.session_state["user_open_positions"] = data["user_open_positions"]
        st.session_state["user_closed_positions"] = data["user_closed_positions"]
        st.session_state["model_open_positions"] = data["model_open_positions"]
        st.session_state["model_closed_positions"] = data["model_closed_positions"]

def create_trade_record(
    ticker: str,
    position_type: str,
    num_shares: int,
    entry_date: str,
    entry_price: float,
    opened_by_user: bool,
    opened_by_model: bool
) -> Dict:
    """
    Returns a dict representing a newly opened trade with a unique ID.
    """
    return {
        "trade_id": str(uuid.uuid4()),
        "ticker": ticker,
        "position_type": position_type,
        "num_shares": num_shares,
        "entry_date": entry_date,       # string or None if not opened yet
        "entry_price": entry_price,     # 0.0 or None if not opened yet
        "status": "open",              # or "scheduled" if pending open
        "opened_by_user": opened_by_user,
        "opened_by_model": opened_by_model,
        "close_date": None,
        "close_price": None,
        "pnl_usd": None,
        "return_pct": None,
        # Optional fields for scheduling
        "pending_open": False,
        "pending_open_date": None,
        "pending_close": False,   # if you do a similar approach for closing
        "pending_close_date": None
    }

def find_trade_by_id(trade_id: str, trades_list: List[Dict]) -> Dict:
    for trade in trades_list:
        if trade["trade_id"] == trade_id:
            return trade
    return None