import os, json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "config_hotels.json")

def load_hotels():
    """Load the hotel list and sheet IDs from config_hotels.json."""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"❌ Missing config file: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["HOTELS"]
