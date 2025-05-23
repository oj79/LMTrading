# Dockerfile
# Use Python 3.12-slim (lightweight, minimal system packages)
FROM python:3.12-slim

# Force Python to flush output immediately, so print(...) appears in logs
ENV PYTHONUNBUFFERED=1

# Create and set a working directory
WORKDIR /app

# Copy all project files (including requirements.txt and TradingApp.py)
COPY . /app

# Install Python dependencies
# Make sure your requirements.txt includes streamlit, google-auth-oauthlib, etc.
RUN pip install --no-cache-dir -r requirements.txt

# Define the port Cloud Run will send traffic to
ENV PORT 8080

# Finally, run Streamlit on the $PORT (Cloud Run expects traffic on 0.0.0.0:$PORT)
CMD streamlit run TradingApp.py --server.port $PORT --server.address 0.0.0.0
