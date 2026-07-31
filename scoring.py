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


def calculate_confidence_score(
    *,
    setup: str,
    structure_score: int,
    operability_score: int,
    bullish_structure: bool,
    macd_positive: bool,
    rsi: float,
    volume_ratio: float,
    distance_resistance: float,
    distance_ema20_pct: float,
) -> int:
    """Misura 0-100 della qualità del setup operativo corrente.

    Lo score è deliberatamente event-driven: il tipo di setup pesa più della
    semplice qualità strutturale dell'asset.
    """
    score = 5

    setup_points = {
        "🟢 Breakout confermato": 38,
        "🟢 Pullback da monitorare": 28,
        "🟡 Breakout da verificare": 21,
        "🟡 Attendere breakout": 16,
        "⚪ Nessun setup": 4,
        "🔴 Falso breakout": -25,
    }
    score += setup_points.get(setup, 0)

    score += round(structure_score * 0.16)
    score += round(operability_score * 0.18)
    score += 8 if bullish_structure else -6
    score += 6 if macd_positive else -6

    if 48 <= rsi <= 66:
        score += 7
    elif 40 <= rsi < 48 or 66 < rsi <= 72:
        score += 3
    elif rsi > 76 or rsi < 28:
        score -= 8

    if volume_ratio >= 1.30:
        score += 8
    elif volume_ratio >= 1.05:
        score += 5
    elif volume_ratio < 0.75:
        score -= 5

    if setup == "🟡 Attendere breakout":
        if 0 <= distance_resistance <= 0.75:
            score += 7
        elif distance_resistance > 2:
            score -= 5

    if setup == "🟢 Pullback da monitorare" and distance_ema20_pct <= 1.0:
        score += 5

    return max(0, min(100, round(score)))


def action_from_confidence(confidence: int, setup: str) -> str:
    if setup == "🔴 Falso breakout":
        return "❌ Evita"
    if setup == "🟢 Breakout confermato" and confidence >= 85:
        return "🚀 Valuta ingresso"
    if setup == "🟢 Pullback da monitorare" and confidence >= 78:
        return "👀 Verifica reazione"
    if confidence >= 78:
        return "🟡 Preparati"
    if confidence >= 62:
        return "⏳ Osserva"
    return "⚪ Nessuna operazione"


def operational_state(setup: str, confidence: int) -> str:
    if setup == "🔴 Falso breakout":
        return "🔴 Setup invalidato"
    if setup == "🟢 Breakout confermato" and confidence >= 85:
        return "🟢 Setup confermato"
    if setup in {"🟡 Breakout da verificare", "🟢 Pullback da monitorare"}:
        return "🟠 Attendere conferma"
    if setup == "🟡 Attendere breakout" or confidence >= 65:
        return "🟡 In avvicinamento"
    return "⚪ Nessuna opportunità"


def setup_progress(setup: str, distance_resistance: float, confidence: int) -> int:
    if setup == "🟢 Breakout confermato":
        return 100
    if setup == "🔴 Falso breakout":
        return 0
    if setup == "🟡 Breakout da verificare":
        return max(65, min(92, confidence))
    if setup == "🟢 Pullback da monitorare":
        return max(60, min(88, confidence))
    if setup == "🟡 Attendere breakout":
        proximity = max(0.0, 1.0 - max(distance_resistance, 0.0) / 2.0)
        return max(45, min(85, round(50 + proximity * 35)))
    return max(5, min(55, round(confidence * 0.65)))


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
    if score >= 85:
        return "🟢 Eccellente"
    if score >= 75:
        return "🟢 Alta"
    if score >= 60:
        return "🟡 Buona"
    if score >= 45:
        return "🟠 Media"
    return "🔴 Bassa"


def confidence_label(score: int) -> str:
    if score >= 90:
        return "A+ · Eccellente"
    if score >= 85:
        return "A · Molto alto"
    if score >= 75:
        return "B · Interessante"
    if score >= 60:
        return "C · Da monitorare"
    return "D · Nessun setup"
