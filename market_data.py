import yfinance as yf
import datetime

def get_latest_price(ticker_symbol: str) -> float:
    try:
        ticker_data = yf.Ticker(ticker_symbol)
        last_day_data = ticker_data.history(period="1d")

        if last_day_data.empty:
            raise ValueError(f"Invalid or no data for ticker: {ticker_symbol}")

        return last_day_data["Close"].iloc[-1]

    except Exception as e:
        # e.g., Network error, etc.
        raise RuntimeError(f"Failed to fetch price for {ticker_symbol}. Reason: {e}")

def get_historical_close_on_or_before(ticker: str, target_date: datetime.date) -> (float, datetime.date):
    """
    Returns (close_price, actual_date_used).
    - If target_date's close price is available, return it.
    - Otherwise, go backward day by day until you find a valid close.
    - Raises ValueError if no data is found in the lookback window.
    """
    # We'll search ~60 days prior to target_date just to be safe
    start_date = target_date - datetime.timedelta(days=60)
    end_date = target_date + datetime.timedelta(days=1)  # yfinance end is exclusive

    df = yf.Ticker(ticker).history(start=start_date, end=end_date)
    if df.empty:
        raise ValueError(f"No historical data for {ticker} in range {start_date} to {target_date}.")

    curr_date = target_date
    while curr_date >= start_date:
        date_str = curr_date.strftime("%Y-%m-%d")
        # Compare with df's DatetimeIndex
        if date_str in df.index.strftime("%Y-%m-%d"):
            row = df.loc[df.index.strftime("%Y-%m-%d") == date_str]
            close_price = row["Close"].iloc[0]
            return (float(close_price), curr_date)
        curr_date -= datetime.timedelta(days=1)

    raise ValueError(f"No available close data on or before {target_date} for {ticker}.")