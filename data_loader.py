from __future__ import annotations
import pandas as pd
import yfinance as yf

class MarketDataError(RuntimeError):
    pass

def download_market_data(ticker: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    try:
        df = yf.download(
            ticker, period=period, interval=interval, auto_adjust=True,
            multi_level_index=False, progress=False, threads=False, prepost=False
        )
    except Exception as exc:
        raise MarketDataError(f"Errore download {ticker}: {exc}") from exc

    if df is None or df.empty:
        raise MarketDataError(f"Nessun dato disponibile per {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    needed = ["Open", "High", "Low", "Close"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise MarketDataError(f"Colonne mancanti per {ticker}: {', '.join(missing)}")

    df = df.copy()
    for c in needed:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["High", "Low", "Close"]).sort_index()
