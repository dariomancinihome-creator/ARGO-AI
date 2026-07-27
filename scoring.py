from __future__ import annotations


def calculate_argo_score(
    price: float,
    ema20: float,
    ema50: float,
    ema200: float,
    rsi: float,
    macd_line: float,
    macd_signal: float,
    daily_change: float,
    distance_support: float,
    distance_resistance: float,
) -> int:
    """Score 0-100 della struttura tecnica, non del punto d'ingresso."""
    score = 50

    score += 6 if price > ema20 else -6
    score += 7 if ema20 > ema50 else -7
    score += 10 if price > ema200 else -14
    score += 9 if ema50 > ema200 else -11

    if 50 <= rsi <= 65:
        score += 9
    elif 40 <= rsi < 50:
        score += 2
    elif 65 < rsi <= 72:
        score += 3
    elif rsi > 75:
        score -= 8
    elif rsi < 25:
        score -= 5

    score += 9 if macd_line > macd_signal else -9
    score += 3 if daily_change > 0 else -3

    if 0 <= distance_support <= 3:
        score += 4
    if 0 <= distance_resistance <= 2:
        score -= 4

    return max(0, min(100, round(score)))


def calculate_operability_score(
    *,
    price: float,
    ema20: float,
    ema50: float,
    ema200: float,
    rsi: float,
    macd_line: float,
    macd_signal: float,
    atr_pct: float,
    distance_support: float,
    distance_resistance: float,
    volume_ratio: float,
    breakout_confirmed: bool,
    breakout_unconfirmed: bool,
    pullback_candidate: bool,
    false_breakout: bool,
) -> int:
    """Score 0-100 della qualità tecnica del punto attuale."""
    score = 35
    bullish_structure = price > ema50 > ema200

    score += 15 if bullish_structure else -15
    score += 10 if macd_line > macd_signal else -10

    if 45 <= rsi <= 65:
        score += 12
    elif 35 <= rsi < 45 or 65 < rsi <= 72:
        score += 4
    elif rsi > 75:
        score -= 15
    elif rsi < 25:
        score -= 8

    if 1.0 <= atr_pct <= 4.5:
        score += 8
    elif atr_pct > 7:
        score -= 12
    elif atr_pct > 5:
        score -= 6

    if false_breakout:
        score -= 25
    elif breakout_confirmed:
        score += 23
        score += 7 if volume_ratio >= 1.10 else 2
    elif breakout_unconfirmed:
        score += 3
        score -= 8 if volume_ratio < 1.0 else 0
    elif pullback_candidate:
        score += 18
    elif 0 <= distance_resistance <= 1.5:
        score -= 12
    elif 1.5 < distance_resistance <= 5:
        score += 4

    if 1 <= distance_support <= 5:
        score += 8
    elif distance_support > 10:
        score -= 8

    return max(0, min(100, round(score)))


def score_label(score: int) -> str:
    if score >= 80:
        return "🟢 Struttura forte"
    if score >= 65:
        return "🟢 Interessante"
    if score >= 50:
        return "🟡 Da osservare"
    if score >= 35:
        return "🟠 Debole"
    return "🔴 Struttura critica"


def operability_label(score: int) -> str:
    if score >= 75:
        return "🟢 Alta"
    if score >= 55:
        return "🟡 Media"
    return "🔴 Bassa"
