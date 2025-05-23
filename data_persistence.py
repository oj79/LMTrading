import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSISTENCE_FILE = os.path.join(BASE_DIR, "data", "trades_data.json")

def load_trades_data():
    if os.path.exists(PERSISTENCE_FILE):
        with open(PERSISTENCE_FILE, "r") as f:
            return json.load(f)
    else:
        return {
            "user_open_positions": [],
            "user_closed_positions": [],
            "model_open_positions": [],
            "model_closed_positions": []
        }

def save_trades_data(data):
    with open(PERSISTENCE_FILE, "w") as f:
        json.dump(data, f)