from __future__ import annotations

from typing import Iterable

import math
import pandas as pd


NUMERIC_REPORT_COLUMNS = (
    "Prezzo", "Var. %", "RSI", "EMA 20", "EMA 50", "EMA 200",
    "MACD", "ATR %", "Supporto", "Resistenza", "Entry", "Stop Loss",
    "TP1", "TP2", "R/R TP1", "R/R TP2", "Rischio/unità",
    "Distanza supporto %", "Distanza resistenza %", "Volume/Media",
)


def to_number(value, default: float | None = None) -> float | None:
    """Converte in float valori numerici, stringhe numeriche e scalar numpy.

    Restituisce default per None, NaN, simboli testuali e valori non convertibili.
    """
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def format_report(
    report: pd.DataFrame,
    numeric_columns: Iterable[str] = NUMERIC_REPORT_COLUMNS,
    decimals: int = 2,
) -> pd.DataFrame:
    """Prepara il report per Streamlit senza applicare round a colonne object.

    Le celle non numeriche nelle colonne quantitative diventano valori mancanti,
    evitando TypeError con pandas/Python recenti.
    """
    formatted = report.copy()
    for column in numeric_columns:
        if column not in formatted.columns:
            continue
        formatted[column] = pd.to_numeric(
            formatted[column], errors="coerce"
        ).round(decimals)
    return formatted


def ensure_columns(report: pd.DataFrame, defaults: dict[str, object]) -> pd.DataFrame:
    """Aggiunge colonne mancanti per tollerare deploy parziali o dati incompleti."""
    result = report.copy()
    for column, default in defaults.items():
        if column not in result.columns:
            result[column] = default
    return result
