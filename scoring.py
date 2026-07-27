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
    """
    Score tecnico 0-100.

    Lo score misura la qualità della struttura tecnica.
    Non è un ordine di acquisto o vendita.
    """
    score = 50

    # Trend di breve e medio periodo
    score += 6 if price > ema20 else -6
    score += 7 if ema20 > ema50 else -7

    # Trend primario: peso maggiore per evitare falsi positivi
    if price > ema200:
        score += 10
    else:
        score -= 14

    if ema50 > ema200:
        score += 9
    else:
        score -= 11

    # RSI
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

    # Momentum
    score += 9 if macd_line > macd_signal else -9

    # Variazione dell'ultima seduta
    score += 3 if daily_change > 0 else -3

    # Posizione nel range recente
    if 0 <= distance_support <= 3:
        score += 4

    if 0 <= distance_resistance <= 2:
        score -= 4

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
