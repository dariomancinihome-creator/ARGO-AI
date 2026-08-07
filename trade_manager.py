from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from supabase_store import (
    insert_trade,
    is_supabase_configured,
    list_trades,
    update_trade,
)

STORE_PATH = Path(__file__).with_name("trades.json")


@dataclass
class TrackedTrade:
    id: str
    asset: str
    ticker: str
    direction: str
    entry: float
    stop_loss: float | None
    tp1: float | None
    tp2: float | None
    setup: str
    opened_at: str
    status: str = "OPEN"
    closed_at: str | None = None
    exit_price: float | None = None


def _secret(name: str, default: str | None = None) -> str | None:
    if st is not None:
        try:
            value = st.secrets.get(name)
            if value not in (None, ""):
                return str(value)
        except Exception:
            pass
    return os.getenv(name, default)


def owner_id() -> str:
    return _secret("ARGO_OWNER_ID", "default-owner") or "default-owner"


def storage_backend() -> str:
    return "Supabase" if is_supabase_configured() else "Locale temporaneo"


def _safe_float(value: Any) -> float | None:
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_local(path: Path = STORE_PATH) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_local(trades: list[dict], path: Path = STORE_PATH) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(trades, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_trades(path: Path = STORE_PATH) -> list[dict]:
    if is_supabase_configured():
        try:
            return list_trades(owner_id())
        except Exception:
            # Non blocchiamo l'intera app in caso di indisponibilità temporanea.
            return _load_local(path)
    return _load_local(path)


def add_trade(
    *,
    asset: str,
    ticker: str,
    entry: float,
    stop_loss: float | None,
    tp1: float | None,
    tp2: float | None,
    setup: str,
    path: Path = STORE_PATH,
) -> dict:
    trade = TrackedTrade(
        id=str(uuid4()),
        asset=asset,
        ticker=ticker,
        direction="LONG",
        entry=float(entry),
        stop_loss=_safe_float(stop_loss),
        tp1=_safe_float(tp1),
        tp2=_safe_float(tp2),
        setup=setup,
        opened_at=_utc_now(),
    )
    payload = asdict(trade)

    if is_supabase_configured():
        try:
            return insert_trade(owner_id(), payload)
        except Exception:
            pass

    trades = _load_local(path)
    trades.append(payload)
    _save_local(trades, path)
    return payload


def close_trade(
    trade_id: str,
    exit_price: float,
    path: Path = STORE_PATH,
) -> None:
    changes = {
        "status": "CLOSED",
        "exit_price": float(exit_price),
        "closed_at": _utc_now(),
    }

    if is_supabase_configured():
        try:
            update_trade(owner_id(), trade_id, changes)
            return
        except Exception:
            pass

    trades = _load_local(path)
    for trade in trades:
        if trade.get("id") == trade_id and trade.get("status") == "OPEN":
            trade.update(changes)
            break
    _save_local(trades, path)


def trade_snapshot(trade: dict, current_price: float) -> dict:
    entry = float(trade["entry"])
    current = float(current_price)
    pnl_pct = ((current / entry) - 1.0) * 100.0 if entry else 0.0
    sl, tp1, tp2 = (
        _safe_float(trade.get(k))
        for k in ("stop_loss", "tp1", "tp2")
    )

    if sl is not None and current <= sl:
        state, action = "🔴 Stop raggiunto", "Piano invalidato"
    elif tp2 is not None and current >= tp2:
        state, action = "🏁 TP2 raggiunto", "Target finale raggiunto"
    elif tp1 is not None and current >= tp1:
        state, action = "🎯 TP1 raggiunto", "Valuta protezione del profitto"
    elif current >= entry:
        state, action = "🟢 Trade in profitto", "Piano ancora attivo"
    else:
        state, action = "🟡 Sotto entry", "Controlla il setup e lo stop"

    def distance(level):
        return None if level is None else ((level / current) - 1.0) * 100.0

    return {
        "pnl_pct": pnl_pct,
        "state": state,
        "action": action,
        "distance_sl": distance(sl),
        "distance_tp1": distance(tp1),
        "distance_tp2": distance(tp2),
    }
