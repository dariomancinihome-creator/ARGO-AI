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

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

st.markdown(
    """
    <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
        [data-testid="stMetricValue"] {font-size: 1.55rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=900, show_spinner=False)
def run_analysis(period: str, interval: str, selected_assets: tuple[str, ...]):
    summaries, histories, errors = [], {}, []

    for name in selected_assets:
        try:
            result = analyse_asset(
                name=name,
                ticker=WATCHLIST[name],
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
        report = report.sort_values(
            ["Operabilità", "Score Struttura"],
            ascending=[False, False],
        ).reset_index(drop=True)

    return report, histories, errors


def format_report(report: pd.DataFrame) -> pd.DataFrame:
    formatted = report.copy()
    decimals = [
        "Prezzo", "Var. %", "RSI", "EMA 20", "EMA 50", "EMA 200",
        "MACD", "ATR %", "Supporto", "Resistenza",
        "Distanza supporto %", "Distanza resistenza %", "Volume/Media",
    ]
    for column in decimals:
        if column in formatted.columns:
            formatted[column] = formatted[column].round(2)
    return formatted


st.title("🚀 ARGO AI 2.1")
st.caption(
    "Struttura tecnica, operabilità e riconoscimento dei setup. "
    "Le indicazioni sono informative e non costituiscono ordini di acquisto o vendita."
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
        "Periodo storico", PERIOD_OPTIONS,
        index=PERIOD_OPTIONS.index(DEFAULT_PERIOD),
    )
    interval = st.selectbox(
        "Intervallo", INTERVAL_OPTIONS,
        index=INTERVAL_OPTIONS.index(DEFAULT_INTERVAL),
    )
    selected_assets = st.multiselect(
        "Asset", options=list(WATCHLIST.keys()), default=list(WATCHLIST.keys())
    )
    top_charts = st.slider(
        "Grafici principali",
        min_value=1,
        max_value=min(6, max(1, len(selected_assets))),
        value=min(TOP_CHARTS_DEFAULT, max(1, len(selected_assets))),
    )
    refresh = st.button("🔄 Aggiorna analisi", use_container_width=True, type="primary")

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
    with st.expander(f"Avvisi durante il download ({len(errors)})"):
        for error in errors:
            st.warning(error)

if report.empty:
    st.error("Non è stato possibile creare il report. Riprova tra qualche minuto.")
    st.stop()

report_display = format_report(report)
best = report.iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capitale", f"€ {capital:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col2.metric("Asset analizzati", len(report))
col3.metric("Migliore operabilità", f"{int(best['Operabilità'])}/100")
col4.metric("Asset in evidenza", best["Asset"])

st.caption("Ultimo aggiornamento app: " + datetime.now().strftime("%d/%m/%Y · %H:%M"))

st.subheader("🏆 Classifica ARGO 2.1")
ranking_columns = [
    "Asset", "Prezzo", "Var. %", "Trend", "Score Struttura",
    "Operabilità", "Setup", "Stato operabilità",
]
st.dataframe(
    report_display[ranking_columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Prezzo": st.column_config.NumberColumn("Prezzo", format="%.2f"),
        "Var. %": st.column_config.NumberColumn("Var. %", format="%.2f%%"),
        "Score Struttura": st.column_config.ProgressColumn(
            "Struttura", min_value=0, max_value=100, format="%d"
        ),
        "Operabilità": st.column_config.ProgressColumn(
            "Operabilità", min_value=0, max_value=100, format="%d"
        ),
    },
)

st.subheader("🎯 Analisi del setup principale")
a, b, c, d = st.columns(4)
a.metric("Asset", best["Asset"])
b.metric("Struttura", f"{int(best['Score Struttura'])}/100")
c.metric("Operabilità", f"{int(best['Operabilità'])}/100")
d.metric("Setup", best["Setup"])

left, right = st.columns(2)
with left:
    st.write(f"**Trend:** {best['Trend']}")
    st.write(f"**RSI:** {best['RSI']:.2f} · {best['Stato RSI']}")
    st.write(f"**MACD:** {best['Segnale MACD']}")
    st.write(f"**Volume/Media 20:** {best['Volume/Media']:.2f}x")
with right:
    st.write(f"**Supporto:** {best['Supporto']:.2f}")
    st.write(f"**Resistenza:** {best['Resistenza']:.2f}")
    st.write(f"**ATR:** {best['ATR %']:.2f}%")
    st.write(f"**Distanza resistenza:** {best['Distanza resistenza %']:.2f}%")

st.info(best["Commento ARGO"])
st.warning(
    "Un breakout è considerato confermato solo dopo una chiusura sopra la resistenza. "
    "Il superamento intraday, da solo, può essere un falso segnale."
)

st.subheader("📈 Grafici principali")
for _, row in report.head(top_charts).iterrows():
    name = row["Asset"]
    with st.expander(
        f"{name} · Operabilità {int(row['Operabilità'])}/100 · {row['Setup']}",
        expanded=(name == best["Asset"]),
    ):
        st.info(row["Commento ARGO"])
        st.plotly_chart(
            price_chart(
                data=histories[name],
                asset_name=name,
                score=int(row["Score Struttura"]),
                support=float(row["Supporto"]),
                resistance=float(row["Resistenza"]),
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            rsi_chart(data=histories[name], asset_name=name),
            use_container_width=True,
        )

st.subheader("📋 Report completo")
st.dataframe(report_display, use_container_width=True, hide_index=True)

csv_data = report_display.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Scarica report CSV",
    data=csv_data,
    file_name="report_argo_2_1.csv",
    mime="text/csv",
)

st.divider()
st.caption(
    "ARGO AI è uno strumento informativo e sperimentale. I dati possono essere "
    "ritardati o differire dalle quotazioni del broker. I CFD comportano un rischio "
    "elevato di perdita, soprattutto con leva."
)
