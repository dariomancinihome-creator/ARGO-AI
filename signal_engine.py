from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import pandas as pd
from indicators import stochastic

@dataclass
class SignalResult:
    asset: str
    signal: str
    k: float | None
    d: float | None
    candle_time: object | None
    reason: str

def _closed_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    yfinance can expose the currently forming 15m bar.
    We deliberately ignore the last row and evaluate only a completed candle.
    """
    if len(df) < 3:
        return df.iloc[0:0]
    return df.iloc[:-1].copy()

def _cross_for_rule(df: pd.DataFrame, rule: dict, direction: str):
    k, d = stochastic(df, *rule["stoch"])
    if len(k) < 2:
        return False, None, None
    k0, d0 = k.iloc[-1], d.iloc[-1]
    kp, dp = k.iloc[-2], d.iloc[-2]
    if pd.isna(k0) or pd.isna(d0) or pd.isna(kp) or pd.isna(dp):
        return False, None, None

    in_zone = rule["k_min"] <= float(k0) < rule["k_max"]
    if direction == "BUY":
        crossed = (kp <= dp) and (k0 > d0)
    else:
        crossed = (kp >= dp) and (k0 < d0)
    return bool(crossed and in_zone), float(k0), float(d0)

def evaluate_asset(asset: str, df: pd.DataFrame, cfg: dict) -> SignalResult:
    closed = _closed_frame(df)
    if len(closed) < 30:
        return SignalResult(asset, "WAIT", None, None, None, "Dati insufficienti")

    buy_ok, buy_k, buy_d = _cross_for_rule(closed, cfg["buy"], "BUY")
    sell_ok, sell_k, sell_d = _cross_for_rule(closed, cfg["sell"], "SELL")
    ts = closed.index[-1]

    if buy_ok and not sell_ok:
        return SignalResult(asset, "BUY", buy_k, buy_d, ts, "Incrocio rialzista validato")
    if sell_ok and not buy_ok:
        return SignalResult(asset, "SELL", sell_k, sell_d, ts, "Incrocio ribassista validato")
    if buy_ok and sell_ok:
        return SignalResult(asset, "WAIT", None, None, ts, "Segnale ambiguo")
    return SignalResult(asset, "WAIT", None, None, ts, "Nessun nuovo incrocio valido")
