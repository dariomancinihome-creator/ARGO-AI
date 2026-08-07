from __future__ import annotations

import os
from typing import Any

import requests

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def _secret(name: str) -> str | None:
    if st is not None:
        try:
            value = st.secrets.get(name)
            if value:
                return str(value)
        except Exception:
            pass
    value = os.getenv(name)
    return str(value) if value else None


def is_supabase_configured() -> bool:
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_ANON_KEY"))


def _headers() -> dict[str, str]:
    key = _secret("SUPABASE_ANON_KEY")
    if not key:
        raise RuntimeError("SUPABASE_ANON_KEY non configurata.")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _endpoint(table: str = "argo_trades") -> str:
    url = _secret("SUPABASE_URL")
    if not url:
        raise RuntimeError("SUPABASE_URL non configurata.")
    return f"{url.rstrip('/')}/rest/v1/{table}"


def list_trades(owner_id: str) -> list[dict[str, Any]]:
    params = {
        "owner_id": f"eq.{owner_id}",
        "select": "*",
        "order": "opened_at.asc",
    }
    response = requests.get(
        _endpoint(),
        headers=_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def insert_trade(owner_id: str, trade: dict[str, Any]) -> dict[str, Any]:
    payload = dict(trade)
    payload["owner_id"] = owner_id
    response = requests.post(
        _endpoint(),
        headers=_headers(),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list) and data:
        return data[0]
    return payload


def update_trade(owner_id: str, trade_id: str, changes: dict[str, Any]) -> None:
    params = {
        "owner_id": f"eq.{owner_id}",
        "id": f"eq.{trade_id}",
    }
    response = requests.patch(
        _endpoint(),
        headers=_headers(),
        params=params,
        json=changes,
        timeout=20,
    )
    response.raise_for_status()
