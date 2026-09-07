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
    price: float | None = None
    candle_open: float | None = None
    candle_high: float | None = None
    candle_low: float | None = None
    candle_close: float | None = None


def _closed_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Evaluate only completed M15 candles.

    Twelve Data can include the currently forming bar. We drop it only when its
    timestamp + 15 minutes is still in the future; otherwise the latest bar is
    already closed and is retained.
    """
    if len(df) < 3:
        return df.iloc[0:0]

    closed = df.copy().sort_index()
    last_ts = pd.Timestamp(closed.index[-1])
    if last_ts.tzinfo is None:
        last_ts = last_ts.tz_localize("UTC")
    else:
        last_ts = last_ts.tz_convert("UTC")

    now = pd.Timestamp(datetime.now(timezone.utc))
    if last_ts + pd.Timedelta(minutes=15) > now:
        closed = closed.iloc[:-1].copy()
    return closed


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


def _result(asset: str, signal: str, k, d, ts, reason: str, row=None) -> SignalResult:
    if row is None:
        return SignalResult(asset, signal, k, d, ts, reason)
    return SignalResult(
        asset=asset,
        signal=signal,
        k=k,
        d=d,
        candle_time=ts,
        reason=reason,
        price=float(row["Close"]),
        candle_open=float(row["Open"]),
        candle_high=float(row["High"]),
        candle_low=float(row["Low"]),
        candle_close=float(row["Close"]),
    )


def evaluate_asset(asset: str, df: pd.DataFrame, cfg: dict) -> SignalResult:
    closed = _closed_frame(df)
    if len(closed) < 30:
        return SignalResult(asset, "WAIT", None, None, None, "Dati insufficienti")

    buy_ok, buy_k, buy_d = _cross_for_rule(closed, cfg["buy"], "BUY")
    sell_ok, sell_k, sell_d = _cross_for_rule(closed, cfg["sell"], "SELL")
    ts = closed.index[-1]
    row = closed.iloc[-1]

    if buy_ok and not sell_ok:
        return _result(asset, "BUY", buy_k, buy_d, ts, "Incrocio rialzista validato", row)
    if sell_ok and not buy_ok:
        return _result(asset, "SELL", sell_k, sell_d, ts, "Incrocio ribassista validato", row)
    if buy_ok and sell_ok:
        return _result(asset, "WAIT", None, None, ts, "Segnale ambiguo", row)
    return _result(asset, "WAIT", None, None, ts, "Nessun nuovo incrocio valido", row)
