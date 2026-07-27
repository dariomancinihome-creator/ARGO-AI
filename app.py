from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from analysis_engine import analyse_asset
from charts import price_chart, rsi_chart
from config import (
    APP_ICON,
    APP_TITLE,
    DEFAULT_CAPITAL,
    DEFAULT_INTERVAL,
    DEFAULT_PERIOD,
    INTERVAL_OPTIONS,
    PERIOD_OPTIONS,
    SUPPORT_RESISTANCE_WINDOW,
    TOP_CHARTS_DEFAULT,
    WATCHLIST,
)


st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
)


st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.55rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=900, show_spinner=False)
def run_analysis(
    period: str,
    interval: str,
    selected_assets: tuple[str, ...],
):
    summaries = []
    histories = {}
    errors = []

    for name in selected_assets:
        ticker = WATCHLIST[name]

        try:
            result = analyse_asset(
                name=name,
                ticker=ticker,
                period=period,
                interval=interval,
                support_window=SUPPORT_RESISTANCE_WINDOW,
            )
            summaries.append(result.summary)
            histories[name] = result.history

        except Exception as exc:
            errors.append(f"{name}: {exc}")

    report = pd.DataFrame(summaries)

    if not report.empty:
        report = (
            report
            .sort_values("Score ARGO", ascending=False)
            .reset_index(drop=True)
        )

    return report, histories, errors


def format_report(report: pd.DataFrame) -> pd.DataFrame:
    formatted = report.copy()

    decimal_columns = [
        "Prezzo",
        "Var. %",
        "RSI",
        "EMA 20",
        "EMA 50",
        "EMA 200",
        "MACD",
        "ATR %",
        "Supporto",
        "Resistenza",
    ]

    for column in decimal_columns:
        if column in formatted.columns:
            formatted[column] = formatted[column].round(2)

    return formatted


st.title("🚀 ARGO AI")
st.caption(
    "Analisi tecnica automatica basata su dati Yahoo Finance. "
    "Lo score descrive la struttura tecnica e non costituisce "
    "un ordine di acquisto o vendita."
)

with st.sidebar:
    st.header("Impostazioni")

    capital = st.number_input(
        "Capitale di riferimento (€)",
        min_value=0.0,
        value=float(DEFAULT_CAPITAL),
        step=10.0,
    )

    period = st.selectbox(
        "Periodo storico",
        PERIOD_OPTIONS,
        index=PERIOD_OPTIONS.index(DEFAULT_PERIOD),
    )

    interval = st.selectbox(
        "Intervallo",
        INTERVAL_OPTIONS,
        index=INTERVAL_OPTIONS.index(DEFAULT_INTERVAL),
    )

    selected_assets = st.multiselect(
        "Asset",
        options=list(WATCHLIST.keys()),
        default=list(WATCHLIST.keys()),
    )

    top_charts = st.slider(
        "Grafici principali",
        min_value=1,
        max_value=min(6, max(1, len(selected_assets))),
        value=min(
            TOP_CHARTS_DEFAULT,
            max(1, len(selected_assets)),
        ),
    )

    refresh = st.button(
        "🔄 Aggiorna analisi",
        use_container_width=True,
        type="primary",
    )

if not selected_assets:
    st.warning("Seleziona almeno un asset nella barra laterale.")
    st.stop()

if refresh:
    st.cache_data.clear()

with st.spinner("ARGO sta scaricando e analizzando i mercati..."):
    report, histories, errors = run_analysis(
        period=period,
        interval=interval,
        selected_assets=tuple(selected_assets),
    )

if errors:
    with st.expander(
        f"Avvisi durante il download ({len(errors)})",
        expanded=False,
    ):
        for error in errors:
            st.warning(error)

if report.empty:
    st.error(
        "Non è stato possibile creare il report. "
        "Riprova tra qualche minuto o cambia periodo/intervallo."
    )
    st.stop()

report_display = format_report(report)
best = report.iloc[0]

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Capitale",
    f"€ {capital:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
)

col2.metric(
    "Asset analizzati",
    len(report),
)

col3.metric(
    "Migliore score",
    f"{int(best['Score ARGO'])}/100",
)

col4.metric(
    "Migliore struttura",
    best["Asset"],
)

st.caption(
    "Ultimo aggiornamento app: "
    + datetime.now().strftime("%d/%m/%Y · %H:%M")
)

st.subheader("🏆 Classifica ARGO")

ranking_columns = [
    "Asset",
    "Prezzo",
    "Var. %",
    "RSI",
    "Trend",
    "Score ARGO",
    "Valutazione",
]

st.dataframe(
    report_display[ranking_columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Prezzo": st.column_config.NumberColumn(
            "Prezzo",
            format="%.2f",
        ),
        "Var. %": st.column_config.NumberColumn(
            "Var. %",
            format="%.2f%%",
        ),
        "RSI": st.column_config.NumberColumn(
            "RSI",
            format="%.2f",
        ),
        "Score ARGO": st.column_config.ProgressColumn(
            "Score ARGO",
            min_value=0,
            max_value=100,
            format="%d",
        ),
    },
)

st.subheader("🔎 Migliore struttura tecnica")

a, b, c, d = st.columns(4)

a.metric("Asset", best["Asset"])
b.metric("Prezzo", f"{best['Prezzo']:.2f}")
c.metric("Variazione", f"{best['Var. %']:.2f}%")
d.metric("Score", f"{int(best['Score ARGO'])}/100")

detail_col1, detail_col2 = st.columns(2)

with detail_col1:
    st.write(f"**Trend:** {best['Trend']}")
    st.write(
        f"**RSI:** {best['RSI']:.2f} · {best['Stato RSI']}"
    )
    st.write(f"**MACD:** {best['Segnale MACD']}")
    st.write(f"**ATR:** {best['ATR %']:.2f}%")

with detail_col2:
    st.write(f"**Supporto:** {best['Supporto']:.2f}")
    st.write(f"**Resistenza:** {best['Resistenza']:.2f}")
    st.write(f"**EMA 20:** {best['EMA 20']:.2f}")
    st.write(f"**EMA 50:** {best['EMA 50']:.2f}")
    st.write(f"**EMA 200:** {best['EMA 200']:.2f}")

st.info(
    "Un punteggio elevato non significa automaticamente che il prezzo "
    "sia in un buon punto d'ingresso. Verifica sempre distanza dalla "
    "resistenza, volatilità, spread, margine e rischio massimo."
)

st.subheader("📈 Grafici principali")

for _, row in report.head(top_charts).iterrows():
    name = row["Asset"]
    history = histories[name]

    with st.expander(
        f"{name} · Score {int(row['Score ARGO'])}/100",
        expanded=(name == best["Asset"]),
    ):
        st.plotly_chart(
            price_chart(
                data=history,
                asset_name=name,
                score=int(row["Score ARGO"]),
            ),
            use_container_width=True,
        )

        st.plotly_chart(
            rsi_chart(
                data=history,
                asset_name=name,
            ),
            use_container_width=True,
        )

st.subheader("📋 Report completo")

st.dataframe(
    report_display,
    use_container_width=True,
    hide_index=True,
)

csv_data = report_display.to_csv(
    index=False,
).encode("utf-8-sig")

st.download_button(
    "⬇️ Scarica report CSV",
    data=csv_data,
    file_name="report_argo.csv",
    mime="text/csv",
)

st.divider()

st.caption(
    "ARGO AI è uno strumento informativo e sperimentale. "
    "I dati possono essere ritardati, incompleti o differire dalle "
    "quotazioni del broker. I CFD sono strumenti complessi e comportano "
    "un rischio elevato di perdita per effetto della leva."
)
