from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()

    data["EMA20"] = EMAIndicator(
        close=data["Close"], window=20
    ).ema_indicator()

    data["EMA50"] = EMAIndicator(
        close=data["Close"], window=50
    ).ema_indicator()

    data["EMA200"] = EMAIndicator(
        close=data["Close"], window=200
    ).ema_indicator()

    data["RSI"] = RSIIndicator(
        close=data["Close"], window=14
    ).rsi()

    macd = MACD(
        close=data["Close"],
        window_slow=26,
        window_fast=12,
        window_sign=9,
    )
    data["MACD"] = macd.macd()
    data["MACD_SIGNAL"] = macd.macd_signal()
    data["MACD_HIST"] = macd.macd_diff()

    atr = AverageTrueRange(
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        window=14,
    )
    data["ATR"] = atr.average_true_range()

    return data.dropna().copy()


def determine_trend(
    price: float,
    ema20: float,
    ema50: float,
    ema200: float,
) -> str:
    if price > ema20 > ema50 > ema200:
        return "🟢 Rialzista forte"

    if price > ema20 > ema50:
        return "🟢 Rialzista"

    if price < ema20 < ema50 < ema200:
        return "🔴 Ribassista forte"

    if price < ema20 < ema50:
        return "🔴 Ribassista"

    return "🟡 Laterale"


def interpret_rsi(rsi: float) -> str:
    if rsi >= 70:
        return "Ipercomprato"

    if rsi <= 30:
        return "Ipervenduto"

    if rsi >= 55:
        return "Positivo"

    if rsi <= 45:
        return "Debole"

    return "Neutro"
