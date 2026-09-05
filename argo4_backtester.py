from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np
import pandas as pd
import yfinance as yf


UNIVERSE = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Nasdaq 100": "NQ=F",
    "S&P 500": "ES=F",
    "DAX": "FDAX.DE",
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "NVIDIA": "NVDA",
    "Tesla": "TSLA",
    "Amazon": "AMZN",
    "Meta": "META",
    "AMD": "AMD",
    "Apple": "AAPL",
}

STOCH_CONFIGS = [(5, 3, 3), (8, 3, 3), (10, 5, 5)]


def download_15m(ticker: str, period: str = "1mo") -> pd.DataFrame:
    df = yf.download(
        ticker, period=period, interval="15m", auto_adjust=True,
        progress=False, threads=False, multi_level_index=False, prepost=False
    )
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    need = ["Open", "High", "Low", "Close", "Volume"]
    for c in need:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[need].dropna(subset=["High", "Low", "Close"]).copy()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev).abs(),
        (df["Low"] - prev).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    a = atr(df, n)
    plus_di = 100 * plus_dm.ewm(alpha=1/n, adjust=False).mean() / a
    minus_di = 100 * minus_dm.ewm(alpha=1/n, adjust=False).mean() / a
    denom = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / denom
    return dx.ewm(alpha=1/n, adjust=False).mean()


def stochastic(df: pd.DataFrame, k_period: int, k_smooth: int, d_period: int):
    ll = df["Low"].rolling(k_period).min()
    hh = df["High"].rolling(k_period).max()
    raw = 100 * (df["Close"] - ll) / (hh - ll).replace(0, np.nan)
    k = raw.rolling(k_smooth).mean()
    d = k.rolling(d_period).mean()
    return k, d


def prepare(df: pd.DataFrame, cfg: tuple[int, int, int]) -> pd.DataFrame:
    x = df.copy()
    x["EMA9"] = ema(x["Close"], 9)
    x["EMA21"] = ema(x["Close"], 21)
    x["EMA9_SLOPE"] = x["EMA9"].pct_change()
    x["ATR"] = atr(x, 14)
    x["ATR_PCT"] = x["ATR"] / x["Close"] * 100
    x["ADX"] = adx(x, 14)
    x["ADX_DELTA"] = x["ADX"].diff()
    x["K"], x["D"] = stochastic(x, *cfg)
    x["BULL_CROSS"] = (x["K"] > x["D"]) & (x["K"].shift(1) <= x["D"].shift(1))
    x["BEAR_CROSS"] = (x["K"] < x["D"]) & (x["K"].shift(1) >= x["D"].shift(1))
    x["RET15"] = x["Close"].shift(-1) / x["Close"] - 1
    x["RET30"] = x["Close"].shift(-2) / x["Close"] - 1
    return x


def _bucket(v):
    if pd.isna(v): return "N/D"
    lo = int(max(0, min(90, math.floor(float(v) / 10) * 10)))
    return f"{lo}-{lo+10}"


def evaluate(df: pd.DataFrame, cfg: tuple[int, int, int], asset: str, ticker: str):
    x = prepare(df, cfg)
    rows = []
    for direction, cross_col in [("BUY", "BULL_CROSS"), ("SELL", "BEAR_CROSS")]:
        sig = x[x[cross_col]].copy()
        if sig.empty:
            continue
        sig["DIR_OK"] = np.where(
            direction == "BUY",
            (sig["EMA9"] > sig["EMA21"]) & (sig["EMA9_SLOPE"] > 0),
            (sig["EMA9"] < sig["EMA21"]) & (sig["EMA9_SLOPE"] < 0),
        )
        sig["ADX_OK"] = (sig["ADX"] >= 18) & (sig["ADX_DELTA"] > 0)
        # Volatility filter is relative to the asset itself, not a hard cross-asset threshold.
        atr_cut = x["ATR_PCT"].quantile(0.40)
        sig["ATR_OK"] = sig["ATR_PCT"] >= atr_cut
        sig["FILTERED"] = sig["DIR_OK"] & sig["ADX_OK"] & sig["ATR_OK"]
        sign = 1 if direction == "BUY" else -1
        sig["WIN15"] = sign * sig["RET15"] > 0
        sig["WIN30"] = sign * sig["RET30"] > 0
        sig["MOVE15"] = sign * sig["RET15"] * 100
        sig["MOVE30"] = sign * sig["RET30"] * 100
        sig["STOCH_ZONE"] = sig["K"].map(_bucket)

        for filtered in [False, True]:
            s = sig if not filtered else sig[sig["FILTERED"]]
            if s.empty:
                continue
            days = max(1, pd.Index(s.index.date).nunique())
            rows.append({
                "Asset": asset,
                "Ticker": ticker,
                "Stoch": f"{cfg[0]}-{cfg[1]}-{cfg[2]}",
                "Direction": direction,
                "Mode": "Cross puro" if not filtered else "+ EMA/ADX/ATR",
                "Signals": len(s),
                "Signals/day": len(s) / days,
                "Win15 %": s["WIN15"].mean() * 100,
                "Win30 %": s["WIN30"].mean() * 100,
                "Move15 %": s["MOVE15"].mean(),
                "Move30 %": s["MOVE30"].mean(),
                "Median ADX": s["ADX"].median(),
                "Median ATR %": s["ATR_PCT"].median(),
                "Best Stoch zone": (
                    s.groupby("STOCH_ZONE")["WIN15"].agg(["mean","count"])
                    .query("count >= 3").sort_values(["mean","count"], ascending=False)
                    .index[0] if len(s.groupby("STOCH_ZONE")["WIN15"].agg(["mean","count"]).query("count >= 3")) else "N/D"
                ),
            })
    return rows


def run_lab(selected_assets: list[str] | None = None):
    assets = selected_assets or list(UNIVERSE)
    summary, errors = [], []
    raw = {}
    for asset in assets:
        ticker = UNIVERSE[asset]
        try:
            df = download_15m(ticker)
            if df.empty:
                errors.append(f"{asset}: nessun dato")
                continue
            raw[asset] = df
            for cfg in STOCH_CONFIGS:
                summary.extend(evaluate(df, cfg, asset, ticker))
        except Exception as exc:
            errors.append(f"{asset}: {exc}")
    result = pd.DataFrame(summary)
    if not result.empty:
        # Balanced score: accuracy + useful frequency + realised directional movement.
        result["Lab Score"] = (
            result["Win15 %"] * 0.55
            + result["Win30 %"] * 0.20
            + np.clip(result["Signals/day"], 0, 8) / 8 * 15
            + np.clip(result["Move15 %"], -0.5, 1.0) * 10
        )
        result = result.sort_values(["Lab Score", "Signals"], ascending=False).reset_index(drop=True)
    return result, errors, raw
