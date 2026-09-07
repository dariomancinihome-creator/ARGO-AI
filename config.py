APP_TITLE = "ARGO 4.1 · Session Trader"
APP_ICON = "⚡"

# Twelve Data uses slash-separated symbols for forex and crypto.
# Trading DNA is intentionally unchanged from ARGO 4.0.
ASSETS = {
    "BTC": {
        "symbol": "BTC/USD",
        "label": "Bitcoin",
        "buy":  {"stoch": (8, 3, 3),  "k_min": 10.0, "k_max": 20.0},
        "sell": {"stoch": (10, 5, 5), "k_min": 80.0, "k_max": 90.0},
    },
    "GBP/USD": {
        "symbol": "GBP/USD",
        "label": "GBP/USD",
        "buy":  {"stoch": (5, 3, 3), "k_min": 10.0, "k_max": 20.0},
        "sell": {"stoch": (8, 3, 3), "k_min": 70.0, "k_max": 80.0},
    },
}

DATA_INTERVAL = "15min"
DATA_OUTPUTSIZE = 120

# Basic Twelve Data allows 8 API credits/minute. Two symbols every 20s = 6 credits/minute.
REFRESH_SECONDS = 20
