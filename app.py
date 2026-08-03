from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from analysis_engine import analyse_asset
from charts import price_chart, rsi_chart
from utils import format_report, to_number
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
        .argo-hero {padding: 1.15rem 1.25rem; border: 1px solid rgba(128,128,128,.28);
                    border-radius: 14px; margin: .25rem 0 1.25rem 0;}
        .argo-hero h2 {margin: 0 0 .35rem 0;}
        .argo-hero p {margin: .15rem 0; font-size: 1.02rem;}
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
        # Compatibilità con dati prodotti da versioni precedenti del motore.
        # Evita il blocco dell'app durante gli aggiornamenti parziali su GitHub.
        if "Confidence" not in report.columns:
            operability = pd.to_numeric(
                report.get("Operabilità", pd.Series(0, index=report.index)),
                errors="coerce",
            ).fillna(0)
            structure = pd.to_numeric(
                report.get("Score Struttura", pd.Series(0, index=report.index)),
                errors="coerce",
            ).fillna(0)
            setup = report.get(
                "Setup", pd.Series("⚪ Nessun setup", index=report.index)
            ).astype(str)
            setup_bonus = setup.map({
                "🟢 Breakout confermato": 24,
                "🟢 Pullback da monitorare": 16,
                "🟡 Breakout da verificare": 10,
                "🟡 Attendere breakout": 6,
                "🔴 Falso breakout": -20,
            }).fillna(0)
            report["Confidence"] = (
                operability * 0.50 + structure * 0.30 + setup_bonus
            ).clip(0, 100).round().astype(int)

        if "Stato operativo" not in report.columns:
            def _fallback_state(row):
                setup = str(row.get("Setup", ""))
                confidence = int(row.get("Confidence", 0))
                if "Falso breakout" in setup:
                    return "🔴 Setup invalidato"
                if "Breakout confermato" in setup and confidence >= 80:
                    return "🟢 Setup confermato"
                if "Breakout da verificare" in setup or "Pullback" in setup:
                    return "🟠 Attendere conferma"
                if "Attendere breakout" in setup or confidence >= 65:
                    return "🟡 In avvicinamento"
                return "⚪ Nessuna opportunità"
            report["Stato operativo"] = report.apply(_fallback_state, axis=1)

        if "Azione" not in report.columns:
            def _fallback_action(row):
                state = str(row.get("Stato operativo", ""))
                confidence = int(row.get("Confidence", 0))
                if "invalidato" in state.lower():
                    return "❌ Evita"
                if "confermato" in state.lower() and confidence >= 85:
                    return "🚀 Valuta ingresso"
                if confidence >= 78:
                    return "🟡 Preparati"
                if confidence >= 62:
                    return "⏳ Osserva"
                return "⚪ Nessuna operazione"
            report["Azione"] = report.apply(_fallback_action, axis=1)

        sort_columns = [
            column for column in ["Confidence", "Operabilità", "Score Struttura"]
            if column in report.columns
        ]
        if sort_columns:
            report = report.sort_values(
                sort_columns, ascending=[False] * len(sort_columns)
            ).reset_index(drop=True)

    return report, histories, errors



def hero_message(report: pd.DataFrame) -> str:
    confirmed = report[report["Stato operativo"] == "🟢 Setup confermato"]
    if not confirmed.empty:
        names = " · ".join(
            f"{row['Asset']} ({int(row['Confidence'])}/100)"
            for _, row in confirmed.head(3).iterrows()
        )
        return (
            f"<div class='argo-hero'><h2>🚀 OGGI ARGO DICE</h2>"
            f"<p><strong>{len(confirmed)} setup operativo/i confermato/i</strong></p>"
            f"<p>{names}</p></div>"
        )

    approaching = report[report["Stato operativo"].isin([
        "🟡 In avvicinamento", "🟠 Attendere conferma"
    ])]
    if not approaching.empty:
        best = approaching.iloc[0]
        return (
            "<div class='argo-hero'><h2>👀 OGGI ARGO DICE</h2>"
            "<p><strong>Nessun setup operativo confermato.</strong></p>"
            f"<p>Il candidato più vicino è {best['Asset']}: "
            f"{best['Stato operativo']} · Confidence {int(best['Confidence'])}/100.</p></div>"
        )

    return (
        "<div class='argo-hero'><h2>⚪ OGGI ARGO DICE</h2>"
        "<p><strong>Nessun setup operativo.</strong></p>"
        "<p>La classifica resta in monitoraggio in attesa di una conferma tecnica.</p></div>"
    )


st.title("🚀 ARGO AI 3.0 RC · Trading Plan")
st.caption(
    "ARGO seleziona i setup, calcola Entry, Stop Loss, TP1, TP2 e rapporto rischio/rendimento. "
    "Il comando ENTRA appare solo quando tutte le regole tecniche della Beta risultano valide. Le indicazioni sono informative e non sono ordini."
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
    risk_pct = st.number_input(
        "Rischio massimo per operazione (%)", min_value=0.1, max_value=5.0,
        value=1.0, step=0.1,
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
variation_label = "Var. candela %" if interval == "1h" else "Var. giorno %"

st.markdown(hero_message(report), unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capitale", f"€ {capital:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col2.metric("Asset analizzati", len(report))
col3.metric("Migliore Confidence", f"{int(best['Confidence'])}/100")
col4.metric("Asset in evidenza", best["Asset"])

st.caption("Ultimo aggiornamento app: " + datetime.now().strftime("%d/%m/%Y · %H:%M"))

st.subheader("🏆 Classifica Decision Engine")
ranking_columns = [
    "Asset", "Prezzo", "Var. %", "Trend", "Confidence", "Conviction", "IQS", "Azione",
    "Entry", "Stop Loss", "TP1", "TP2", "R/R TP1", "Stato operativo", "Progresso setup", "Setup",
]
ranking = report_display[ranking_columns].rename(columns={"Var. %": variation_label})
st.dataframe(
    ranking,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Prezzo": st.column_config.NumberColumn("Prezzo", format="%.2f"),
        variation_label: st.column_config.NumberColumn(variation_label, format="%.2f%%"),
        "Confidence": st.column_config.ProgressColumn(
            "Confidence", min_value=0, max_value=100, format="%d"
        ),
        "Progresso setup": st.column_config.ProgressColumn(
            "Avanzamento", min_value=0, max_value=100, format="%d%%"
        ),
        "Score Struttura": st.column_config.ProgressColumn(
            "Struttura", min_value=0, max_value=100, format="%d"
        ),
        "Operabilità": st.column_config.ProgressColumn(
            "Operabilità", min_value=0, max_value=100, format="%d"
        ),
    },
)

st.subheader("🎯 Migliore candidato del momento")
a, b, c, d, e, f = st.columns(6)
a.metric("Asset", best["Asset"])
b.metric("Confidence", f"{int(best['Confidence'])}/100")
c.metric("Classe", best["Classe Confidence"])
d.metric("Stato", best["Stato operativo"])
e.metric("Azione", best["Azione"])
f.metric("IQS", best["IQS"])

left, right = st.columns(2)
with left:
    st.write(f"**Trend:** {best['Trend']}")
    st.write(f"**Struttura:** {int(best['Score Struttura'])}/100 · {best['Valutazione']}")
    st.write(f"**Operabilità:** {int(best['Operabilità'])}/100 · {best['Stato operabilità']}")
    st.write(f"**Setup:** {best['Setup']}")
with right:
    st.write(f"**RSI:** {best['RSI']:.2f} · {best['Stato RSI']}")
    st.write(f"**MACD:** {best['Segnale MACD']}")
    st.write(f"**Volume/Media 20:** {best['Volume/Media']:.2f}x")
    st.write(f"**Distanza resistenza:** {best['Distanza resistenza %']:.2f}%")

st.progress(int(best["Progresso setup"]), text=f"Avanzamento setup: {int(best['Progresso setup'])}%")
st.info(best["Commento ARGO"])

st.subheader("🧭 Piano operativo")
if str(best.get("Piano valido", False)).lower() in {"true", "1", "yes"}:
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Entry", f"{best['Entry']:.4f}")
    p2.metric("Stop Loss", f"{best['Stop Loss']:.4f}")
    p3.metric("TP1", f"{best['TP1']:.4f}")
    p4.metric("TP2", f"{best['TP2']:.4f}")
    p5.metric("R/R TP1", f"{best['R/R TP1']:.2f}")
    risk_amount = capital * risk_pct / 100
    risk_per_unit = to_number(best.get("Rischio/unità"), 0.0) or 0.0
    units = risk_amount / risk_per_unit if risk_per_unit > 0 else 0.0
    st.success(
        f"🚀 ENTRA — piano tecnico validato. Con rischio {risk_pct:.1f}% su € {capital:,.2f}, "
        f"rischio monetario € {risk_amount:,.2f} e quantità teorica {units:.4f} unità."
    )
else:
    st.warning(best.get("Esito piano", "Nessun piano operativo validato."))
    st.caption("ARGO non mostra ENTRA finché breakout, Confidence, volume, RSI, stop tecnico e R/R non superano tutti i filtri.")

st.subheader("📈 Grafici principali")
for _, row in report.head(top_charts).iterrows():
    name = row["Asset"]
    with st.expander(
        f"{name} · Confidence {int(row['Confidence'])}/100 · {row['Azione']}",
        expanded=(name == best["Asset"]),
    ):
        st.write(f"**{row['Stato operativo']} · {row['Setup']}**")
        st.progress(int(row["Progresso setup"]), text=f"Avanzamento setup: {int(row['Progresso setup'])}%")
        st.info(row["Commento ARGO"])
        st.plotly_chart(
            price_chart(
                data=histories[name],
                asset_name=name,
                score=int(row["Score Struttura"]),
                support=float(row["Supporto"]),
                resistance=float(row["Resistenza"]),
                entry=to_number(row.get("Entry")),
                stop_loss=to_number(row.get("Stop Loss")),
                tp1=to_number(row.get("TP1")),
                tp2=to_number(row.get("TP2")),
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
    file_name="report_argo_3_0_rc.csv",
    mime="text/csv",
)

st.divider()
st.caption(
    "ARGO AI è uno strumento informativo e sperimentale. I dati possono essere "
    "ritardati o differire dalle quotazioni del broker. I CFD comportano un rischio "
    "elevato di perdita, soprattutto con leva."
)
