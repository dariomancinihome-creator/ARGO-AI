import streamlit as st
import pandas as pd
from argo4_backtester import UNIVERSE, run_lab

st.set_page_config(page_title="ARGO 4.0 Lab", page_icon="🧪", layout="wide")
st.title("🧪 ARGO 4.0 — Laboratorio M15")
st.caption("22 sessioni circa / ultimo mese disponibile. Il laboratorio misura i segnali; non invia ordini.")

with st.sidebar:
    st.header("Universo")
    defaults = ["Gold","Nasdaq 100","Bitcoin","NVIDIA","Tesla","Amazon","EUR/USD","GBP/USD"]
    selected = st.multiselect("Asset da testare", list(UNIVERSE), default=defaults)
    st.markdown("**Strategie in gara:** 5-3-3 · 8-3-3 · 10-5-5")
    st.markdown("Filtro: EMA 9/21 + ADX14 crescente + ATR relativo")
    run = st.button("▶ ESEGUI LABORATORIO", type="primary", use_container_width=True)

if not run:
    st.info("Seleziona gli asset e premi ESEGUI LABORATORIO.")
    st.stop()

if not selected:
    st.warning("Seleziona almeno un asset.")
    st.stop()

with st.spinner("Scarico M15 e processo tutte le configurazioni..."):
    result, errors, raw = run_lab(selected)

if errors:
    with st.expander("Download non riusciti / note"):
        for e in errors:
            st.write("•", e)

if result.empty:
    st.error("Nessun risultato disponibile.")
    st.stop()

best = result.iloc[0]
c1,c2,c3,c4 = st.columns(4)
c1.metric("Miglior asset", best["Asset"])
c2.metric("Configurazione", best["Stoch"])
c3.metric("Win 15m", f'{best["Win15 %"]:.1f}%')
c4.metric("Segnali/giorno", f'{best["Signals/day"]:.1f}')

st.subheader("🏆 Classifica quantitativa")
show_cols = ["Asset","Stoch","Direction","Mode","Signals","Signals/day","Win15 %","Win30 %",
             "Move15 %","Move30 %","Median ADX","Median ATR %","Best Stoch zone","Lab Score"]
st.dataframe(
    result[show_cols].style.format({
        "Signals/day":"{:.2f}","Win15 %":"{:.1f}","Win30 %":"{:.1f}",
        "Move15 %":"{:.3f}","Move30 %":"{:.3f}",
        "Median ADX":"{:.1f}","Median ATR %":"{:.3f}","Lab Score":"{:.1f}"
    }),
    use_container_width=True, height=620
)

st.subheader("Top 10 — filtro completo")
filtered = result[result["Mode"] == "+ EMA/ADX/ATR"].head(10)
st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

st.download_button(
    "⬇ Scarica risultati CSV",
    result.to_csv(index=False).encode("utf-8"),
    "argo4_lab_results.csv",
    "text/csv",
    use_container_width=True,
)

st.caption("Nota: un Win15 positivo significa solo che il prezzo dopo 15 minuti era nella direzione del segnale. "
           "Non include spread, slippage o costi del broker; questi vanno aggiunti prima di valutare l'operatività reale.")
