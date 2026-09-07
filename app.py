from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from config import APP_TITLE, APP_ICON, ASSETS, DATA_INTERVAL, DATA_OUTPUTSIZE, REFRESH_SECONDS
from data_loader import download_market_data, MarketDataError
from signal_engine import evaluate_asset

ROME = ZoneInfo("Europe/Rome")

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1050px; padding-top: 1.5rem;}
.signal-card {border:1px solid rgba(128,128,128,.28);border-radius:18px;padding:1.25rem;margin:.4rem 0;}
.big-signal {font-size:2.4rem;font-weight:800;line-height:1.1;}
.asset {font-size:1.15rem;font-weight:700;opacity:.8;}
.small {opacity:.68;font-size:.9rem;}
.feed-ok {font-weight:700;}
</style>
""", unsafe_allow_html=True)

for key, default in {
    "session_active": False,
    "session_started": None,
    "last_signal_key": {},
    "signal_count": 0,
    "signal_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("⚡ ARGO 4.1")
st.caption("SESSION TRADER · BTC + GBP/USD · M15 · TWELVE DATA")

try:
    TWELVE_DATA_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]
except Exception:
    TWELVE_DATA_API_KEY = ""

if not TWELVE_DATA_API_KEY:
    st.error("API key Twelve Data non configurata. Inserisci TWELVE_DATA_API_KEY nei Secrets di Streamlit.")
    st.code('TWELVE_DATA_API_KEY = "INCOLLA_QUI_LA_TUA_API_KEY"', language="toml")
    st.stop()

left, right = st.columns(2)
with left:
    if not st.session_state.session_active:
        if st.button("▶ AVVIA SESSIONE", type="primary", use_container_width=True):
            st.session_state.session_active = True
            st.session_state.session_started = datetime.now(timezone.utc)
            st.session_state.last_signal_key = {}
            st.session_state.signal_count = 0
            st.rerun()
    else:
        if st.button("■ TERMINA SESSIONE", use_container_width=True):
            st.session_state.session_active = False
            st.rerun()

with right:
    status = "🟢 SESSIONE ATTIVA" if st.session_state.session_active else "⚪ ARGO A RIPOSO"
    st.metric("Stato", status)


def seconds_to_next_quarter():
    now = datetime.now(timezone.utc)
    elapsed = (now.minute % 15) * 60 + now.second
    return 15 * 60 - elapsed if elapsed else 15 * 60


def fmt_price(asset: str, value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}" if asset == "BTC" else f"{value:.5f}"


def fmt_rome(ts) -> str:
    if ts is None:
        return "—"
    stamp = pd.Timestamp(ts)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert(ROME).strftime("%d/%m/%Y %H:%M")


def record_signal(asset: str, result) -> None:
    key = f"{result.candle_time}|{result.signal}"
    if st.session_state.last_signal_key.get(asset) == key:
        return

    st.session_state.last_signal_key[asset] = key
    st.session_state.signal_count += 1

    emitted = datetime.now(ROME)
    st.session_state.signal_log.append({
        "Asset": asset,
        "Direzione": result.signal,
        "Ora segnale": emitted.strftime("%d/%m/%Y %H:%M:%S"),
        "Prezzo ARGO": result.price,
        "Candela M15": fmt_rome(result.candle_time),
        "Open": result.candle_open,
        "High": result.candle_high,
        "Low": result.candle_low,
        "Close": result.candle_close,
    })


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def live_session():
    remaining = seconds_to_next_quarter()
    mm, ss = divmod(remaining, 60)

    a, b, c = st.columns(3)
    a.metric("Prossima chiusura M15", f"{mm:02d}:{ss:02d}")
    if st.session_state.session_started:
        elapsed = datetime.now(timezone.utc) - st.session_state.session_started
        total = int(elapsed.total_seconds())
        eh, rem = divmod(total, 3600)
        em, es = divmod(rem, 60)
        b.metric("Sessione", f"{eh:02d}:{em:02d}:{es:02d}")
    c.metric("Segnali sessione", st.session_state.signal_count)

    results = []
    for asset, cfg in ASSETS.items():
        try:
            df = download_market_data(
                cfg["symbol"],
                api_key=TWELVE_DATA_API_KEY,
                interval=DATA_INTERVAL,
                outputsize=DATA_OUTPUTSIZE,
            )
            result = evaluate_asset(asset, df, cfg)
            latest = df.iloc[-1]
            latest_time = fmt_rome(df.index[-1])
            latest_price = float(latest["Close"])
        except MarketDataError as exc:
            result = None
            latest_time = "—"
            latest_price = None
            st.error(f"{asset}: {exc}")
        except Exception as exc:
            result = None
            latest_time = "—"
            latest_price = None
            st.error(f"{asset}: errore analisi — {exc}")
        results.append((asset, cfg, result, latest_time, latest_price))

    cols = st.columns(2)
    for col, (asset, cfg, result, latest_time, latest_price) in zip(cols, results):
        with col:
            st.markdown(f"**Feed: TWELVE DATA · M15**  \nUltimo dato: {latest_time} · Prezzo: {fmt_price(asset, latest_price)}")

            if result is None:
                st.markdown(
                    f"<div class='signal-card'><div class='asset'>{asset}</div><div class='big-signal'>⚠️ DATA</div></div>",
                    unsafe_allow_html=True,
                )
                continue

            icon = {"BUY": "🟢", "SELL": "🔴", "WAIT": "⚪"}[result.signal]
            if result.signal in ("BUY", "SELL") and result.candle_time is not None:
                record_signal(asset, result)

            candle = fmt_rome(result.candle_time)
            kd = f"K {result.k:.1f} · D {result.d:.1f}" if result.k is not None else "In attesa"

            st.markdown(
                f"<div class='signal-card'>"
                f"<div class='asset'>{asset}</div>"
                f"<div class='big-signal'>{icon} {result.signal}</div>"
                f"<div>{kd}</div>"
                f"<div class='small'>{result.reason}</div>"
                f"<div class='small'>Ultima candela valutata: {candle}</div>"
                f"<div class='small'>Close M15 ARGO: {fmt_price(asset, result.price)}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.caption("ARGO registra il segnale e la candela M15 che lo ha generato. Nessun TP, SL o risultato viene calcolato.")

    if st.session_state.signal_log:
        st.subheader("📒 Registro segnali")
        log_df = pd.DataFrame(st.session_state.signal_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Scarica registro CSV",
            data=log_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="argo_4_1_segnali.csv",
            mime="text/csv",
            use_container_width=True,
        )


if st.session_state.session_active:
    live_session()
else:
    st.info("Premi AVVIA SESSIONE. ARGO non analizza i mercati finché la sessione non è attiva.")
    if st.session_state.signal_log:
        st.subheader("📒 Registro segnali")
        log_df = pd.DataFrame(st.session_state.signal_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Scarica registro CSV",
            data=log_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="argo_4_1_segnali.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.success("Feed dati live: Twelve Data · M15. DNA BUY/SELL invariato rispetto ad ARGO 4.0.")
