from __future__ import annotations

import pandas as pd
import yfinance as yf


class MarketDataError(RuntimeError):
    pass


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [
            col[0] if isinstance(col, tuple) else col
            for col in df.columns
        ]
    return df


def download_market_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            multi_level_index=False,
            progress=False,
            threads=False,
        )
    except Exception as exc:
        raise MarketDataError(f"Errore download {ticker}: {exc}") from exc

    if df is None or df.empty:
        raise MarketDataError(f"Nessun dato disponibile per {ticker}")

    df = _flatten_columns(df)

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise MarketDataError(
            f"Colonne mancanti per {ticker}: {', '.join(missing)}"
        )

    df = df[required].copy()

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["High", "Low", "Close"])

    if df.empty:
        raise MarketDataError(f"Dati non validi per {ticker}")

    return df
