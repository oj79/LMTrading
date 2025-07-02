LMTrading
=========

LMTrading is a Streamlit application that demonstrates how to combine language models with simple trade management features.
Users sign in with Google OAuth, submit trading ideas for critique by an OpenAI model, and record open or closed positions in Google Firestore.

Features
--------
* **Google OAuth sign in** – users authenticate with their Google account.
* **LLM trade critique** – ideas are sent to OpenAI's API to obtain an analysis and a **FOLLOW/REJECT** decision.
* **Trade management** – open positions immediately or schedule them for the future, close trades, and automatically track unrealised PnL.
* **Firestore persistence** – user accounts and trades are stored in Firestore collections.
* **Market data** – prices are fetched with `yfinance`.

Setup
-----
1. Clone this repository and create a Python environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and set the following variables:

   ```text
   OPENAI_API_KEY=<your-openai-key>
   GOOGLE_CLIENT_ID=<google-oauth-client-id>
   GOOGLE_CLIENT_SECRET=<google-oauth-client-secret>
   APP_DOMAIN=<app-url-used-for-oauth-redirect>
   ALLOWED_EMAILS=<comma-separated-list-of-allowed-emails>
   PROJECT_ID=<gcp-project-id-for-firestore>
   ```
   You also need Google Cloud credentials available for Firestore access. A service
   account JSON file pointed to by the standard
   `GOOGLE_APPLICATION_CREDENTIALS` environment variable works well.

Running
-------
Start the application locally using Streamlit:

```bash
streamlit run TradingApp.py
```

The app will open in your browser.  If you deploy to Cloud Run or a similar service,
ensure the environment variables above are provided.

Docker
------
A `Dockerfile` is included.  Build and run with:

```bash
docker build -t lmtrading .
docker run -p 8080:8080 --env-file .env lmtrading
```

Note: If you wish to try to application, please send me your email so that I can make you an allowed user

Files
-----
* `TradingApp.py` – main Streamlit interface and app logic.
* `llm_critique.py` – helper that calls the OpenAI API to critique ideas.
* `position_management.py` – wrappers around Firestore operations for opening,
  closing, and scheduling trades.
* `firestore_database.py` – Firestore queries and persistence functions.
* `market_data.py` – fetches market prices via `yfinance`.
* `auth_state_db.py` – small helper to store temporary OAuth state in Firestore.

This repository contains minimal example code and is not a complete
trading system.  Use it as a starting point to experiment with
Streamlit, Firestore and OpenAI integrations.