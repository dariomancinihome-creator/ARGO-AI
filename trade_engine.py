from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradePlan:
    direction: str
    entry: float | None
    stop_loss: float | None
    tp1: float | None
    tp2: float | None
    rr1: float | None
    rr2: float | None
    risk_per_unit: float | None
    valid: bool
    reason: str


def _round_price(value: float | None) -> float | None:
    if value is None:
        return None
    if abs(value) >= 1000:
        return round(value, 1)
    if abs(value) >= 10:
        return round(value, 2)
    return round(value, 4)


def build_long_trade_plan(
    *,
    setup: str,
    confidence: int,
    close: float,
    candle_low: float,
    atr: float,
    breakout_level: float,
    next_resistance: float | None,
    volume_ratio: float,
    rsi: float,
) -> TradePlan:
    """Crea un piano long solo per breakout effettivamente confermati.

    Regole beta 3.0:
    - entry: chiusura della candela di conferma;
    - stop: sotto il minimo della candela e sotto il livello rotto, con buffer 0,5 ATR;
    - TP1: 2R;
    - TP2: resistenza superiore utile, se almeno 2,5R; altrimenti 3R.
    """
    if setup != "🟢 Breakout confermato":
        return TradePlan("LONG", None, None, None, None, None, None, None, False,
                         "Piano non attivo: il breakout non è confermato.")

    if atr <= 0 or close <= 0:
        return TradePlan("LONG", None, None, None, None, None, None, None, False,
                         "Piano non disponibile: volatilità o prezzo non validi.")

    entry = close
    structural_floor = min(candle_low, breakout_level)
    stop = structural_floor - (0.50 * atr)
    risk = entry - stop

    if risk <= 0:
        return TradePlan("LONG", None, None, None, None, None, None, None, False,
                         "Stop tecnico non coerente con il prezzo di ingresso.")

    risk_atr = risk / atr
    tp1 = entry + 2.0 * risk
    candidate_tp2 = entry + 3.0 * risk
    if next_resistance is not None and next_resistance > entry:
        candidate_rr = (next_resistance - entry) / risk
        if candidate_rr >= 2.5:
            candidate_tp2 = next_resistance

    rr1 = (tp1 - entry) / risk
    rr2 = (candidate_tp2 - entry) / risk

    checks = {
        "confidence": confidence >= 90,
        "volume": volume_ratio >= 1.05,
        "rsi": 50 <= rsi <= 72,
        "stop": 0.25 <= risk_atr <= 5.0,
        "rr": rr1 >= 2.0,
    }
    valid = all(checks.values())
    missing = [name for name, ok in checks.items() if not ok]
    reason = (
        "Piano operativo validato dalle regole ARGO 3.0 Beta."
        if valid
        else "Piano calcolato ma non autorizzato: manca " + ", ".join(missing) + "."
    )

    return TradePlan(
        direction="LONG",
        entry=_round_price(entry),
        stop_loss=_round_price(stop),
        tp1=_round_price(tp1),
        tp2=_round_price(candidate_tp2),
        rr1=round(rr1, 2),
        rr2=round(rr2, 2),
        risk_per_unit=_round_price(risk),
        valid=valid,
        reason=reason,
    )


def position_size(capital: float, risk_pct: float, risk_per_unit: float | None) -> float | None:
    if capital <= 0 or risk_pct <= 0 or not risk_per_unit or risk_per_unit <= 0:
        return None
    return round((capital * risk_pct / 100.0) / risk_per_unit, 4)
