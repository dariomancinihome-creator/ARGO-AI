from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

from data_loader import download_market_data
from indicators import add_indicators, determine_trend, interpret_rsi
from scoring import (
    calculate_argo_score,
    calculate_operability_score,
    operability_label,
    score_label,
)


@dataclass
class AssetAnalysis:
    summary: dict
    history: pd.DataFrame


def _setup_comment(
    *,
    name: str,
    setup: str,
    resistance: float,
    support: float,
    rsi: float,
    macd_positive: bool,
    volume_ratio: float,
) -> str:
    macd_text = "favorevole" if macd_positive else "non favorevole"

    if setup == "🟢 Breakout confermato":
        return (
            f"{name} ha chiuso sopra la resistenza di {resistance:.2f}. "
            f"Il MACD è {macd_text}, l'RSI è {rsi:.1f} e i volumi sono "
            f"{volume_ratio:.2f} volte la media delle ultime 20 candele. "
            "Il breakout è tecnicamente confermato. Prima di qualunque operazione "
            "restano necessari stop, obiettivo e rischio massimo prestabilito."
        )

    if setup == "🟡 Breakout da verificare":
        return (
            f"{name} ha superato la resistenza di {resistance:.2f}, ma manca una "
            f"conferma completa: MACD {macd_text}, RSI {rsi:.1f}, volumi "
            f"{volume_ratio:.2f} volte la media. ARGO attende una chiusura stabile "
            "e una partecipazione dei volumi più convincente."
        )

    if setup == "🟡 Attendere breakout":
        return (
            f"{name} è vicino alla resistenza di {resistance:.2f}, ma non l'ha ancora "
            "superata con una chiusura confermata. Un semplice superamento intraday "
            "non è sufficiente: ARGO attende chiusura sopra il livello, MACD favorevole, "
            "RSI non eccessivo e possibilmente volumi in aumento."
        )

    if setup == "🟢 Pullback da monitorare":
        return (
            f"{name} mantiene una struttura rialzista e sta ritracciando verso una "
            "zona tecnica di breve periodo. Il setup richiede una reazione positiva; "
            "lo stop teorico deve restare sotto un supporto identificabile."
        )

    if setup == "🔴 Falso breakout":
        return (
            f"{name} aveva superato la precedente resistenza, ma è tornato sotto "
            f"{resistance:.2f}. La configurazione non è confermata e il rischio di "
            "falso breakout è elevato."
        )

    return (
        f"Al momento {name} non presenta un setup tecnico completo. "
        f"Supporto recente {support:.2f}, resistenza recente {resistance:.2f}. "
        "ARGO resta in osservazione."
    )


def _completed_bars_only(data: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Remove the latest still-open intraday bar before confirming a setup."""
    interval_minutes = {"1h": 60}.get(interval)
    if interval_minutes is None or data.empty:
        return data

    last_timestamp = pd.Timestamp(data.index[-1])
    if last_timestamp.tzinfo is None:
        last_timestamp = last_timestamp.tz_localize("UTC")
    else:
        last_timestamp = last_timestamp.tz_convert("UTC")

    bar_close = last_timestamp + pd.Timedelta(minutes=interval_minutes)
    now_utc = pd.Timestamp.now(tz="UTC")
    if bar_close > now_utc:
        return data.iloc[:-1]
    return data


def analyse_asset(
    name: str,
    ticker: str,
    period: str,
    interval: str,
    support_window: int = 20,
    closed_candles_only: bool = False,
) -> AssetAnalysis:
    raw = download_market_data(ticker, period, interval)
    if closed_candles_only:
        raw = _completed_bars_only(raw, interval)
    data = add_indicators(raw)

    minimum_rows = max(3, support_window + 2)
    if len(data) < minimum_rows:
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

    # Il livello corrente esclude la candela in corso/ultima candela disponibile.
    prior_range = data.iloc[-(support_window + 1):-1]
    support = float(prior_range["Low"].min())
    resistance = float(prior_range["High"].max())

    # Serve a riconoscere se la candela precedente aveva rotto un livello più vecchio.
    older_range = data.iloc[-(support_window + 2):-2]
    older_resistance = float(older_range["High"].max())

    distance_support = ((price - support) / price) * 100
    distance_resistance = ((resistance - price) / price) * 100

    volume_avg = float(prior_range["Volume"].tail(20).mean())
    current_volume = float(last["Volume"])
    volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1.0

    macd_positive = macd_line > macd_signal
    bullish_structure = price > ema50 > ema200
    price_broke_resistance = price > resistance and previous_price <= resistance

    breakout_confirmed = (
        price_broke_resistance
        and macd_positive
        and rsi <= 72
        and volume_ratio >= 1.05
    )
    breakout_unconfirmed = price_broke_resistance and not breakout_confirmed
    false_breakout = previous_price > older_resistance and price < older_resistance
    pullback_candidate = (
        bullish_structure
        and abs((price - ema20) / price * 100) <= 2.0
        and macd_positive
        and 40 <= rsi <= 65
    )

    if false_breakout:
        setup = "🔴 Falso breakout"
    elif breakout_confirmed:
        setup = "🟢 Breakout confermato"
    elif breakout_unconfirmed:
        setup = "🟡 Breakout da verificare"
    elif 0 <= distance_resistance <= 2.0 and bullish_structure:
        setup = "🟡 Attendere breakout"
    elif pullback_candidate:
        setup = "🟢 Pullback da monitorare"
    else:
        setup = "⚪ Nessun setup"

    structure_score = calculate_argo_score(
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

    operability_score = calculate_operability_score(
        price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi=rsi,
        macd_line=macd_line,
        macd_signal=macd_signal,
        atr_pct=atr_pct,
        distance_support=distance_support,
        distance_resistance=distance_resistance,
        volume_ratio=volume_ratio,
        breakout_confirmed=breakout_confirmed,
        breakout_unconfirmed=breakout_unconfirmed,
        pullback_candidate=pullback_candidate,
        false_breakout=false_breakout,
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
        "Segnale MACD": "🟢 Positivo" if macd_positive else "🔴 Negativo",
        "ATR %": atr_pct,
        "Supporto": support,
        "Resistenza": resistance,
        "Distanza supporto %": distance_support,
        "Distanza resistenza %": distance_resistance,
        "Volume/Media": volume_ratio,
        "Trend": determine_trend(price, ema20, ema50, ema200),
        "Score Struttura": structure_score,
        "Valutazione": score_label(structure_score),
        "Operabilità": operability_score,
        "Stato operabilità": operability_label(operability_score),
        "Setup": setup,
        "Commento ARGO": _setup_comment(
            name=name,
            setup=setup,
            resistance=resistance,
            support=support,
            rsi=rsi,
            macd_positive=macd_positive,
            volume_ratio=volume_ratio,
        ),
    }

    return AssetAnalysis(summary=summary, history=data)
