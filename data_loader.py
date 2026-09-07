from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import pandas as pd


class MarketDataError(RuntimeError):
    pass


def download_market_data(
    symbol: str,
    api_key: str,
    interval: str = "15min",
    outputsize: int = 120,
) -> pd.DataFrame:
    """Download OHLC candles from Twelve Data, returned oldest -> newest in UTC."""
    if not api_key:
        raise MarketDataError("Twelve Data API key mancante")

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": int(outputsize),
        "order": "ASC",
        "timezone": "UTC",
        "apikey": api_key,
    }
    url = "https://api.twelvedata.com/time_series?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "ARGO/4.1"})

    try:
        with urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 429:
            raise MarketDataError("Limite crediti Twelve Data raggiunto; attendi il minuto successivo") from exc
        raise MarketDataError(f"Errore HTTP Twelve Data ({exc.code})") from exc
    except (URLError, TimeoutError) as exc:
        raise MarketDataError(f"Twelve Data non raggiungibile: {exc}") from exc
    except Exception as exc:
        raise MarketDataError(f"Errore lettura Twelve Data: {exc}") from exc

    if isinstance(payload, dict) and payload.get("status") == "error":
        message = payload.get("message") or payload.get("code") or "errore sconosciuto"
        raise MarketDataError(f"Twelve Data: {message}")

    values = payload.get("values") if isinstance(payload, dict) else None
    if not values:
        raise MarketDataError(f"Nessun dato disponibile per {symbol}")

    df = pd.DataFrame(values)
    needed = ["datetime", "open", "high", "low", "close"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise MarketDataError(f"Colonne mancanti per {symbol}: {', '.join(missing)}")

    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["datetime"]).set_index("datetime")
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})

    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Volume" in df.columns:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")

    return df.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
