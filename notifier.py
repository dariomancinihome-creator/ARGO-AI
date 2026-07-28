from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


PUSHOVER_ENDPOINT = "https://api.pushover.net/1/messages.json"


class NotificationError(RuntimeError):
    """Raised when Pushover rejects or cannot receive a notification."""


def send_pushover(
    *,
    user_key: str,
    api_token: str,
    title: str,
    message: str,
    url: str | None = None,
    url_title: str = "Apri ARGO",
    priority: int = 0,
    sound: str = "pushover",
    timeout_seconds: int = 20,
) -> dict:
    if not user_key or not api_token:
        raise NotificationError("Credenziali Pushover mancanti")

    payload: dict[str, str | int] = {
        "user": user_key,
        "token": api_token,
        "title": title,
        "message": message,
        "priority": priority,
        "sound": sound,
    }
    if url:
        payload["url"] = url
        payload["url_title"] = url_title

    request = urllib.request.Request(
        PUSHOVER_ENDPOINT,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise NotificationError(
            f"Pushover HTTP {exc.code}: {details}"
        ) from exc
    except urllib.error.URLError as exc:
        raise NotificationError(f"Connessione Pushover fallita: {exc}") from exc

    result = json.loads(body)
    if result.get("status") != 1:
        raise NotificationError(f"Pushover ha rifiutato il messaggio: {result}")
    return result
