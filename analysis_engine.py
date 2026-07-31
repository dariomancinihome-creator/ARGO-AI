from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_loader import download_market_data
from indicators import add_indicators, determine_trend, interpret_rsi
from scoring import (
    action_from_confidence,
    calculate_argo_score,
    calculate_confidence_score,
    calculate_operability_score,
    confidence_label,
    operational_state,
    operability_label,
    score_label,
    setup_progress,
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
    confidence: int,
    distance_resistance: float,
) -> str:
    macd_text = "favorevole" if macd_positive else "non favorevole"

    if setup == "🟢 Breakout confermato":
        return (
            f"{name} ha chiuso sopra la resistenza di {resistance:.2f}. "
            f"MACD {macd_text}, RSI {rsi:.1f} e volumi a {volume_ratio:.2f}x "
            f"la media. Confidence {confidence}/100: il setup è confermato, ma "
            "l'eventuale ingresso va valutato solo dopo avere definito stop, target "
            "e perdita massima accettabile."
        )

    if setup == "🟡 Breakout da verificare":
        return (
            f"{name} ha superato la resistenza di {resistance:.2f}, ma la qualità "
            f"della conferma non è ancora sufficiente. MACD {macd_text}, RSI {rsi:.1f}, "
            f"volumi {volume_ratio:.2f}x. Perché non entrare adesso: ARGO attende una "
            "chiusura stabile e una partecipazione dei volumi più convincente."
        )

    if setup == "🟡 Attendere breakout":
        return (
            f"{name} mantiene una struttura interessante ed è a "
            f"{max(distance_resistance, 0):.2f}% dalla resistenza di {resistance:.2f}. "
            "Perché non entrare adesso: il breakout non è ancora avvenuto. Il setup "
            "potrà diventare operativo solo con chiusura sopra il livello, MACD "
            "favorevole, RSI non eccessivo e possibilmente volumi in aumento."
        )

    if setup == "🟢 Pullback da monitorare":
        return (
            f"{name} conserva una struttura rialzista e sta ritracciando verso una "
            "zona tecnica di breve periodo. Perché non entrare subito: manca ancora "
            "una reazione positiva leggibile. ARGO attende il recupero del momentum "
            "prima di considerare il pullback confermato."
        )

    if setup == "🔴 Falso breakout":
        return (
            f"{name} aveva superato una precedente resistenza, ma è tornato sotto "
            f"{resistance:.2f}. Il setup è invalidato: il rischio di falso breakout "
            "resta elevato e ARGO non considera opportuno inseguire il prezzo."
        )

    return (
        f"{name} non presenta ancora un evento operativo completo. Supporto recente "
        f"{support:.2f}, resistenza {resistance:.2f}. Perché non entrare adesso: manca "
        "una conferma tecnica chiara. ARGO resta in osservazione."
    )


def analyse_asset(
    name: str,
    ticker: str,
    period: str,
    interval: str,
    support_window: int = 20,
) -> AssetAnalysis:
    raw = download_market_data(ticker, period, interval)
    data = add_indicators(raw)

    minimum_rows = max(3, support_window + 2)
    if len(data) < minimum_rows:
        raise ValueError(f"Indicatori insufficienti per {name}")

    last = data.iloc[-1]
    previous = data.iloc[-2]

    price = float(last["Close"])
    previous_price = float(previous["Close"])
    candle_change = ((price / previous_price) - 1) * 100

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    ema200 = float(last["EMA200"])
    rsi = float(last["RSI"])
    macd_line = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])
    atr = float(last["ATR"])
    atr_pct = (atr / price) * 100 if price else 0.0

    prior_range = data.iloc[-(support_window + 1):-1]
    support = float(prior_range["Low"].min())
    resistance = float(prior_range["High"].max())

    older_range = data.iloc[-(support_window + 2):-2]
    older_resistance = float(older_range["High"].max())

    distance_support = ((price - support) / price) * 100
    distance_resistance = ((resistance - price) / price) * 100
    distance_ema20_pct = abs((price - ema20) / price * 100)

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
        and distance_ema20_pct <= 2.0
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
        daily_change=candle_change,
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

    confidence = calculate_confidence_score(
        setup=setup,
        structure_score=structure_score,
        operability_score=operability_score,
        bullish_structure=bullish_structure,
        macd_positive=macd_positive,
        rsi=rsi,
        volume_ratio=volume_ratio,
        distance_resistance=distance_resistance,
        distance_ema20_pct=distance_ema20_pct,
    )
    action = action_from_confidence(confidence, setup)
    state = operational_state(setup, confidence)
    progress = setup_progress(setup, distance_resistance, confidence)

    summary = {
        "Asset": name,
        "Ticker": ticker,
        "Prezzo": price,
        "Var. %": candle_change,
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
        "Confidence": confidence,
        "Classe Confidence": confidence_label(confidence),
        "Progresso setup": progress,
        "Stato operativo": state,
        "Azione": action,
        "Commento ARGO": _setup_comment(
            name=name,
            setup=setup,
            resistance=resistance,
            support=support,
            rsi=rsi,
            macd_positive=macd_positive,
            volume_ratio=volume_ratio,
            confidence=confidence,
            distance_resistance=distance_resistance,
        ),
    }

    return AssetAnalysis(summary=summary, history=data)
