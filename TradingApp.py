import streamlit as st
import datetime
import secrets
from urllib.parse import urlencode
import requests

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Import your position management that references Firestore:
from position_management import (
    open_new_trade,
    schedule_open_trade,
    close_trade,
    update_unrealized_pnl,
    auto_open_scheduled_trades,
    find_trade_by_id
)
# Import your LLM critique function
from llm_critique import get_critique_and_decision
# For historical price or latest price
from market_data import get_latest_price, get_historical_close_on_or_before

# Import the new Firestore-based auth state logic:
from auth_state_db import store_oauth_state, verify_and_consume_oauth_state

###########################################
# [CHANGEME #1]: Environment Variables / Config
###########################################
import os
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
APP_DOMAIN = os.getenv("APP_DOMAIN", "")
# Comma-separated list of allowed emails => turn into a set
ALLOWED_EMAILS = set(os.getenv("ALLOWED_EMAILS", "").split(","))

################################################
# Build Google OAuth URL (using Firestore state)
################################################
def build_google_oauth_url():
    scope = "openid email profile"
    redirect_uri = f"{APP_DOMAIN}?page=callback"
    # Instead of st.session_state, we store state in Firestore:
    state = store_oauth_state()

    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,  # The Firestore doc ID
        "prompt": "consent",
        "access_type": "offline"
    }
    return base_url + "?" + urlencode(params)


################################################
# Exchange Code & Verify ID Token
################################################
def exchange_code_for_tokens(code):
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = f"{APP_DOMAIN}?page=callback"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    resp = requests.post(token_url, data=data)
    resp.raise_for_status()
    return resp.json()

def verify_id_token_str(id_token_str):
    idinfo = id_token.verify_oauth2_token(
        id_token_str,
        google_requests.Request(),
        CLIENT_ID
    )
    return idinfo


################################################
# Handle Google Callback
################################################
def handle_google_callback(query_params):
    code = query_params.get("code", [None])[0]
    returned_state = query_params.get("state", [None])[0]
    print(f"[DEBUG callback] code={code}, state={returned_state}")

    if not code:
        st.error("Missing 'code' parameter from Google OAuth callback.")
        return

    # If we have no returned_state, check if user is already logged in
    if not returned_state:
        if st.session_state.get("logged_in"):
            # Already logged in => remove ?page=callback, then rerun => show main UI
            st.experimental_set_query_params()
            st.rerun()
        else:
            st.error("State mismatch. Potential CSRF or session expired.")
        return

    # If the doc isn't found => might be a second callback
    if not verify_and_consume_oauth_state(returned_state):
        if st.session_state.get("logged_in"):
            # Already logged in => remove callback param, rerun => main UI
            st.experimental_set_query_params()
            st.rerun()
        else:
            st.error("State mismatch. Potential CSRF or session expired.")
        return

    # If we made it here => first successful callback => proceed
    try:
        tokens = exchange_code_for_tokens(code)
        id_token_str = tokens["id_token"]
        info = verify_id_token_str(id_token_str)

        user_email = info.get("email", "")
        if not user_email:
            st.error("No email found in ID token.")
            return

        # Mark user as logged in
        st.session_state["user_email"] = user_email
        st.session_state["logged_in"] = True

        # We'll store user_id from the ID token "sub"
        user_id = info["sub"]
        st.session_state["user_id"] = user_id

        # Create a Firestore user doc if not exist
        from firestore_database import create_user_if_not_exists
        create_user_if_not_exists(user_id, user_email)

        # Successful first callback => remove ?page=callback, then rerun => main UI
        st.experimental_set_query_params()
        st.rerun()

    except Exception as ex:
        st.error(f"Login failed: {ex}")


################################################
# Show Login Screen
################################################
def show_login_screen():
    st.title("Sign In Required")
    st.write("Please sign in with Google to continue.")
    auth_url = build_google_oauth_url()
    st.markdown(f"[**Sign in with Google**]({auth_url})")


################################################
# Main Entry Point
################################################
def main():
    # Check if this is a callback
    query_params = st.experimental_get_query_params()
    page = query_params.get("page", [None])[0]
    if page == "callback":
        handle_google_callback(query_params)
        return

    # If not logged in => show sign in
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        show_login_screen()
        return

    # If user email not allowed => reject
    user_email = st.session_state.get("user_email", "")
    if user_email not in ALLOWED_EMAILS:
        st.error("Access Denied. Your email is not on the allowed list.")
        return

    # Otherwise => run the product
    run_product_app()


################################################
# The Product Logic (Preserving All Features)
################################################
def run_product_app():
    # 1) Auto-open any scheduled trades
    auto_open_scheduled_trades()

    st.title("Trading LLM Product - Full Firestore Integration")

    # 2) LLM critique
    user_idea = st.text_area("Enter your trade idea (type any idea you want):")
    if st.button("Get Decision & Critique"):
        from llm_critique import get_critique_and_decision
        result = get_critique_and_decision(user_idea)
        critique_text = result["critique"]
        st.write("**Analyses and Decision**")
        st.write(critique_text)

        st.session_state["critique_text"] = critique_text
        st.session_state["show_open_trade_form"] = True

    # 3) If user wants to open a trade
    if st.session_state.get("show_open_trade_form", False):
        with st.form(key="open_trade_form"):
            st.write("Do YOU want to open a position anyway?")
            user_wants_to_open = st.selectbox("Open this trade?", ["No", "Yes"])

            ticker = st.text_input("Enter the stock ticker for accuracy")
            position_type = st.selectbox("Position Type", ["long", "short"])
            num_shares = st.number_input("Number of shares", min_value=1, value=10)
            entry_date = st.date_input("Entry Date (Past, Today, or Future)")

            submitted = st.form_submit_button("Submit")
            if submitted and user_wants_to_open == "Yes":
                from market_data import get_historical_close_on_or_before
                today = datetime.date.today()
                model_follows = ("FOLLOW" in st.session_state.get("critique_text", ""))

                if entry_date < today:
                    # immediate open with historical approach
                    try:
                        price, actual_date_used = get_historical_close_on_or_before(ticker, entry_date)
                        # Firestore: open trade immediately
                        open_new_trade(
                            ticker=ticker,
                            position_type=position_type,
                            num_shares=num_shares,
                            entry_date=str(actual_date_used),
                            entry_price=price,
                            opened_by_user=True,
                            opened_by_model=model_follows
                        )
                        st.success("Trade opened successfully!")
                    except ValueError as e:
                        st.error(f"Could not open trade: {e}")

                elif entry_date == today:
                    # schedule for today's close
                    #from position_management import schedule_open_trade
                    schedule_open_trade(
                        ticker=ticker,
                        position_type=position_type,
                        num_shares=num_shares,
                        scheduled_date=str(entry_date),
                        opened_by_user=True,
                        opened_by_model=model_follows
                    )
                    st.info("Trade scheduled to open *today* at the market close.")

                else:
                    # future date => schedule
                    schedule_open_trade(
                        ticker=ticker,
                        position_type=position_type,
                        num_shares=num_shares,
                        scheduled_date=str(entry_date),
                        opened_by_user=True,
                        opened_by_model=model_follows
                    )
                    st.info(f"Trade scheduled to open on {entry_date} at that day's close.")

                st.session_state["show_open_trade_form"] = False

    st.write("---")

    # 4) Update PnL for all open positions each rerun
    update_unrealized_pnl()

    # 5) Display user open positions
    st.subheader("User's Open Positions")
    _render_open_positions()

    st.write("---")

    # (Optionally show model open positions, if you store them separately)

    # 6) Display closed positions
    st.subheader("User's Closed Positions")
    _render_closed_positions()


def _render_open_positions():
    from position_management import get_user_open_positions
    open_positions = get_user_open_positions(st.session_state["user_id"])
    if not open_positions:
        st.write("No open positions.")
        return

    import pandas as pd
    data_for_df = []
    for pos in open_positions:
        data_for_df.append({
            "Trade ID": pos["trade_id"],
            "Ticker": pos["ticker"],
            "Type": pos["positionType"],
            "Shares": pos["numShares"],
            "Entry Date": pos["entryDate"],
            "Entry Price": pos["entryPrice"],
            "Unreal. PnL (USD)": pos.get("unrealized_pnl_usd", 0),
            "Unreal. Return (%)": pos.get("unrealized_return_pct", 0),
        })
    df = pd.DataFrame(data_for_df)
    df.index += 1
    df.index.name = "Index"
    st.dataframe(df)

    trade_id_to_close = st.selectbox("Select a Trade to Close", ["None"] + [p["trade_id"] for p in open_positions])
    if trade_id_to_close != "None":
        close_option = st.selectbox("Close Price Source", ["User Entered", "Use Today's Close"])
        user_close_price = st.number_input("Manual Close Price", min_value=0.0, value=100.0)
        close_date = st.date_input("Close Date", datetime.date.today())
        if st.button("Close Position"):
            from position_management import close_trade
            from market_data import get_latest_price
            selected_pos = find_trade_by_id(trade_id_to_close, open_positions)
            if not selected_pos:
                st.error("Trade not found in the open positions list.")
                return

            if close_option == "Use Today's Close":
                actual_close_price = get_latest_price(selected_pos["ticker"])
            else:
                actual_close_price = user_close_price

            close_trade(
                trade_id=trade_id_to_close,
                close_price=actual_close_price,
                close_date=str(close_date)
            )
            st.success(f"Position {trade_id_to_close} closed at {actual_close_price}!")
            st.rerun()


def _render_closed_positions():
    from position_management import get_user_closed_positions
    closed_positions = get_user_closed_positions(st.session_state["user_id"])
    if not closed_positions:
        st.write("No closed positions.")
        return

    import pandas as pd
    data_for_df = []
    for pos in closed_positions:
        data_for_df.append({
            "Trade ID": pos["trade_id"],
            "Ticker": pos["ticker"],
            "Type": pos["positionType"],
            "Shares": pos["numShares"],
            "Entry Date": pos["entryDate"],
            "Entry Price": pos["entryPrice"],
            "Close Date": pos["closeDate"],
            "Close Price": pos["closePrice"],
            "PnL (USD)": pos.get("pnl_usd", 0),
            "Return (%)": pos.get("return_pct", 0),
        })
    df = pd.DataFrame(data_for_df)
    df.index += 1
    df.index.name = "Index"
    st.dataframe(df)


if __name__ == "__main__":
    main()
