import streamlit as st
from argo4_backtester import UNIVERSE,run_lab,filter_impact

st.set_page_config(page_title="ARGO 4.0 Test 2",page_icon="🧬",layout="wide")
st.title("🧬 ARGO 4.0 — Test 2: chirurgia dei filtri")
st.caption("Obiettivo: misurare quanto errore elimina ogni filtro e quanti segnali sacrifica.")

with st.sidebar:
    defaults=["Gold","Nasdaq 100","Bitcoin","NVIDIA","Tesla","Amazon","EUR/USD","GBP/USD"]
    selected=st.multiselect("Asset da testare",list(UNIVERSE),default=defaults)
    st.markdown("**Livelli:** Stoch → +EMA → +ADX → +ATR")
    run=st.button("▶ ESEGUI TEST 2",type="primary",use_container_width=True)

if not run:
    st.info("Premi ESEGUI TEST 2.")
    st.stop()
if not selected:
    st.warning("Seleziona almeno un asset."); st.stop()

with st.spinner("Backtest M15 incrementale in corso..."):
    result,errors=run_lab(selected)
impact=filter_impact(result)

if errors:
    with st.expander("Note download"):
        for e in errors: st.write("•",e)
if result.empty:
    st.error("Nessun risultato."); st.stop()

# Focus on rows with a minimally useful sample.
robust=result[result["Signals"]>=10]
best=(robust.iloc[0] if not robust.empty else result.iloc[0])
a,b,c,d=st.columns(4)
a.metric("Asset",best["Asset"])
b.metric("Setup",f'{best["Stoch"]} {best["Direction"]}')
c.metric("Errore 15m",f'{best["Error15 %"]:.1f}%')
d.metric("Segnali/giorno",f'{best["Signals/day"]:.2f}')

st.subheader("1. Frontiera frequenza / errore")
cols=["Asset","Stoch","Direction","Filter level","Signals","Signals/day",
      "Win15 %","Error15 %","Win30 %","Error30 %","Signals retained %","Signals removed %",
      "Move15 %","Move30 %","Efficiency score"]
st.dataframe(result[cols].style.format({
    "Signals/day":"{:.2f}","Win15 %":"{:.1f}","Error15 %":"{:.1f}",
    "Win30 %":"{:.1f}","Error30 %":"{:.1f}","Signals retained %":"{:.1f}",
    "Signals removed %":"{:.1f}","Move15 %":"{:.3f}","Move30 %":"{:.3f}",
    "Efficiency score":"{:.1f}"
}),use_container_width=True,height=650)

st.subheader("2. Costo di ogni filtro")
icols=["Asset","Stoch","Direction","Filter level","Signals","Signals/day",
       "Base error %","Error15 %","Errors reduced pp","Signals sacrificed",
       "Signals removed %","pp error reduction / 10% signals lost"]
st.dataframe(impact[icols].sort_values(["Asset","Stoch","Direction","Filter level"]),
             use_container_width=True,height=650)

st.subheader("3. Candidati con almeno 10 segnali")
st.dataframe(robust[cols].head(25),use_container_width=True,hide_index=True)

st.download_button("⬇ Scarica Test 2 CSV",impact.to_csv(index=False).encode("utf-8"),
                   "argo4_test2.csv","text/csv",use_container_width=True)
st.caption("Il test misura direzione a +15/+30m. Spread, slippage, leva e costi non sono inclusi.")
