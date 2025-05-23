import streamlit as st
from firestore_database import (
    create_trade_record,
    schedule_trade_record,
    auto_open_scheduled_trades as fs_auto_open_scheduled_trades,  # renamed here
    close_trade_in_firestore,
    update_unrealized_pnl as fs_update_unrealized_pnl,
    get_user_open_positions,
    get_user_closed_positions
)

def open_new_trade(ticker, position_type, num_shares, entry_date, entry_price,
                   opened_by_user, opened_by_model):
    """
    Immediately opens a trade record with a known entry_date and entry_price (like original).
    Now implemented via Firestore.
    """
    user_id = st.session_state["user_id"]
    return create_trade_record(
        user_id, ticker, position_type, num_shares,
        entry_date, entry_price,
        opened_by_user, opened_by_model,
        status="open", pending_open=False
    )

def schedule_open_trade(ticker, position_type, num_shares, scheduled_date,
                        opened_by_user, opened_by_model):
    """
    Creates a trade record not yet opened, marking it scheduled in Firestore.
    """
    user_id = st.session_state["user_id"]
    return schedule_trade_record(
        user_id, ticker, position_type, num_shares,
        scheduled_date, opened_by_user, opened_by_model
    )

def auto_open_scheduled_trades():
    """
    Each rerun, finalize any scheduled trades that are now in the past or today in Firestore.
    Calls the real Firestore function 'fs_auto_open_scheduled_trades'.
    """
    return fs_auto_open_scheduled_trades()

def close_trade(trade_id, close_price, close_date):
    """
    Closes a trade in Firestore, computing PnL.
    """
    close_trade_in_firestore(trade_id, close_price, close_date)

def update_unrealized_pnl():
    """
    On every rerun, fetch latest price, recalc unrealized PnL in Firestore.
    """
    fs_update_unrealized_pnl()

def find_trade_by_id(trade_id, trades_list):
    """
    If needed, you can still keep a helper for searching in a local list.
    But in Firestore, we typically do a direct doc fetch.
    For backwards compatibility, we'll just do a naive approach:
    """
    for t in trades_list:
        if t["trade_id"] == trade_id:
            return t
    return None