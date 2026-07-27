from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_loader import download_market_data
from indicators import add_indicators, determine_trend, interpret_rsi
from scoring import calculate_argo_score, score_label


@dataclass
class AssetAnalysis:
    summary: dict
    history: pd.DataFrame


def analyse_asset(
    name: str,
    ticker: str,
    period: str,
    interval: str,
    support_window: int = 20,
) -> AssetAnalysis:
    raw = download_market_data(ticker, period, interval)
    data = add_indicators(raw)

    if len(data) < 2:
        raise ValueError(f"Indicatori insufficienti per {name}")

    last = data.iloc[-1]
    previous = data.iloc[-2]

    price = float(last["Close"])
    previous_price = float(previous["Close"])
    daily_change = ((price / previous_price) - 1) * 100

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    ema200 = float(last["EMA200"])
    rsi = float(last["RSI"])
    macd_line = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])
    atr = float(last["ATR"])
    atr_pct = (atr / price) * 100 if price else 0.0

    recent = data.tail(max(2, support_window))
    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    distance_support = ((price - support) / price) * 100
    distance_resistance = ((resistance - price) / price) * 100

    score = calculate_argo_score(
        price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi=rsi,
        macd_line=macd_line,
        macd_signal=macd_signal,
        daily_change=daily_change,
        distance_support=distance_support,
        distance_resistance=distance_resistance,
    )

    summary = {
        "Asset": name,
        "Ticker": ticker,
        "Prezzo": price,
        "Var. %": daily_change,
        "RSI": rsi,
        "Stato RSI": interpret_rsi(rsi),
        "EMA 20": ema20,
        "EMA 50": ema50,
        "EMA 200": ema200,
        "MACD": macd_line,
        "Segnale MACD": (
            "🟢 Positivo"
            if macd_line > macd_signal
            else "🔴 Negativo"
        ),
        "ATR %": atr_pct,
        "Supporto": support,
        "Resistenza": resistance,
        "Trend": determine_trend(price, ema20, ema50, ema200),
        "Score ARGO": score,
        "Valutazione": score_label(score),
    }

    return AssetAnalysis(summary=summary, history=data)
