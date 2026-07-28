from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis_engine import analyse_asset
from config import SUPPORT_RESISTANCE_WINDOW, WATCHLIST
from notifier import NotificationError, send_pushover

ALERT_PERIOD = os.getenv("ARGO_ALERT_PERIOD", "60d")
ALERT_INTERVAL = os.getenv("ARGO_ALERT_INTERVAL", "1h")
MIN_OPERABILITY = int(os.getenv("ARGO_MIN_OPERABILITY", "75"))
MIN_STRUCTURE = int(os.getenv("ARGO_MIN_STRUCTURE", "65"))
TOP_CANDIDATES = int(os.getenv("ARGO_TOP_CANDIDATES", "5"))
ARGO_APP_URL = os.getenv(
    "ARGO_APP_URL",
    "https://argo-ai-k8zczq2nxkpvirrpdsmzwm.streamlit.app/",
)
STATE_PATH = Path(os.getenv("ARGO_STATE_PATH", ".argo_state/alert_state.json"))


@dataclass(frozen=True)
class Candidate:
    summary: dict[str, Any]
    candle_time: str

    @property
    def signal_id(self) -> str:
        return "|".join(
            [
                str(self.summary["Ticker"]),
                str(self.summary["Setup"]),
                self.candle_time,
            ]
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(path: Path = STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"sent": {}, "runs": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"sent": {}, "runs": []}
    state.setdefault("sent", {})
    state.setdefault("runs", [])
    return state


def save_state(state: dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def _prune_state(state: dict[str, Any], max_signals: int = 500, max_runs: int = 100) -> None:
    sent_items = list(state.get("sent", {}).items())
    if len(sent_items) > max_signals:
        state["sent"] = dict(sent_items[-max_signals:])
    state["runs"] = state.get("runs", [])[-max_runs:]


def scan_market() -> tuple[list[Candidate], list[str]]:
    candidates: list[Candidate] = []
    errors: list[str] = []

    for name, ticker in WATCHLIST.items():
        try:
            result = analyse_asset(
                name=name,
                ticker=ticker,
                period=ALERT_PERIOD,
                interval=ALERT_INTERVAL,
                support_window=SUPPORT_RESISTANCE_WINDOW,
                closed_candles_only=True,
            )
            summary = result.summary
            candle_time = result.history.index[-1].isoformat()
            candidates.append(Candidate(summary=summary, candle_time=candle_time))
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    candidates.sort(
        key=lambda item: (
            int(item.summary["Operabilità"]),
            int(item.summary["Score Struttura"]),
        ),
        reverse=True,
    )
    return candidates[:TOP_CANDIDATES], errors


def is_actionable(candidate: Candidate) -> bool:
    summary = candidate.summary
    return (
        summary.get("Setup") == "🟢 Breakout confermato"
        and int(summary.get("Operabilità", 0)) >= MIN_OPERABILITY
        and int(summary.get("Score Struttura", 0)) >= MIN_STRUCTURE
    )


def _grade(candidate: Candidate) -> str:
    operability = int(candidate.summary["Operabilità"])
    structure = int(candidate.summary["Score Struttura"])
    if operability >= 90 and structure >= 80:
        return "A+"
    if operability >= 82 and structure >= 72:
        return "A"
    return "B"


def _notification_text(candidate: Candidate) -> tuple[str, str]:
    s = candidate.summary
    title = f"🚨 ARGO AI · Setup {_grade(candidate)}"
    message = (
        f"{s['Asset']} ({s['Ticker']})\n"
        f"{s['Setup']}\n"
        f"Prezzo: {float(s['Prezzo']):.2f}\n"
        f"Operabilità: {int(s['Operabilità'])}/100 · "
        f"Struttura: {int(s['Score Struttura'])}/100\n"
        f"RSI: {float(s['RSI']):.1f} · Volume: {float(s['Volume/Media']):.2f}x\n"
        f"Resistenza: {float(s['Resistenza']):.2f}\n"
        "Apri ARGO e verifica grafico, rischio e piano operativo."
    )
    return title, message


def run_alert_cycle(*, send_test: bool = False) -> dict[str, Any]:
    user_key = os.getenv("PUSHOVER_USER_KEY", "").strip()
    api_token = os.getenv("PUSHOVER_API_TOKEN", "").strip()
    if not user_key or not api_token:
        raise RuntimeError(
            "Mancano PUSHOVER_USER_KEY o PUSHOVER_API_TOKEN nei GitHub Secrets"
        )

    if send_test:
        send_pushover(
            user_key=user_key,
            api_token=api_token,
            title="✅ ARGO AI collegato",
            message=(
                "Il motore di notifiche push è attivo. "
                "Da ora gli alert reali partiranno solo quando un setup confermato "
                "supera le soglie impostate."
            ),
            url=ARGO_APP_URL,
        )
        return {"test": True, "sent": 1, "errors": []}

    state = load_state()
    candidates, errors = scan_market()
    sent_now: list[str] = []

    for candidate in candidates:
        if not is_actionable(candidate):
            continue
        if candidate.signal_id in state["sent"]:
            continue

        title, message = _notification_text(candidate)
        try:
            response = send_pushover(
                user_key=user_key,
                api_token=api_token,
                title=title,
                message=message,
                url=ARGO_APP_URL,
                priority=0,
                sound="cashregister",
            )
        except NotificationError as exc:
            errors.append(f"{candidate.summary['Asset']}: {exc}")
            continue

        state["sent"][candidate.signal_id] = {
            "asset": candidate.summary["Asset"],
            "ticker": candidate.summary["Ticker"],
            "setup": candidate.summary["Setup"],
            "candle_time": candidate.candle_time,
            "sent_at": _now_iso(),
            "receipt": response.get("request"),
        }
        sent_now.append(candidate.signal_id)

    state["runs"].append(
        {
            "run_at": _now_iso(),
            "candidates": [
                {
                    "asset": c.summary["Asset"],
                    "ticker": c.summary["Ticker"],
                    "operability": int(c.summary["Operabilità"]),
                    "structure": int(c.summary["Score Struttura"]),
                    "setup": c.summary["Setup"],
                    "candle_time": c.candle_time,
                }
                for c in candidates
            ],
            "sent": sent_now,
            "errors": errors,
        }
    )
    _prune_state(state)
    save_state(state)

    return {
        "test": False,
        "analysed": len(WATCHLIST),
        "candidates": len(candidates),
        "sent": len(sent_now),
        "errors": errors,
    }


if __name__ == "__main__":
    test_mode = os.getenv("ARGO_SEND_TEST", "false").lower() in {"1", "true", "yes"}
    result = run_alert_cycle(send_test=test_mode)
    print(json.dumps(result, indent=2, ensure_ascii=False))
