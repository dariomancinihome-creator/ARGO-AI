APP_TITLE = "ARGO 4.0 · Session Trader"
APP_ICON = "⚡"

ASSETS = {
    "BTC": {
        "ticker": "BTC-USD",
        "label": "Bitcoin",
        "buy":  {"stoch": (8, 3, 3),  "k_min": 10.0, "k_max": 20.0},
        "sell": {"stoch": (10, 5, 5), "k_min": 80.0, "k_max": 90.0},
    },
    "GBP/USD": {
        "ticker": "GBPUSD=X",
        "label": "GBP/USD",
        "buy":  {"stoch": (5, 3, 3), "k_min": 10.0, "k_max": 20.0},
        "sell": {"stoch": (8, 3, 3), "k_min": 70.0, "k_max": 80.0},
    },
}

DATA_PERIOD = "5d"
DATA_INTERVAL = "15m"
REFRESH_SECONDS = 10
