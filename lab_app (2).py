import streamlit as st
from argo4_backtester import UNIVERSE,run_dna

st.set_page_config(page_title="ARGO 4.0 Test 3",page_icon="🧬",layout="wide")
st.title("🧬 ARGO 4.0 — Test 3: DNA degli incroci")
st.caption("Cerchiamo dove nascono gli errori senza aggiungere altri indicatori.")

with st.sidebar:
    defaults=["Gold","Nasdaq 100","Bitcoin","NVIDIA","Tesla","Amazon","EUR/USD","GBP/USD"]
    selected=st.multiselect("Asset",list(UNIVERSE),default=defaults)
    run=st.button("▶ ESEGUI TEST 3",type="primary",use_container_width=True)

if not run: st.info("Premi ESEGUI TEST 3."); st.stop()
if not selected: st.warning("Seleziona almeno un asset."); st.stop()

with st.spinner("Analizzo il DNA di ogni incrocio M15..."):
    events,zones,hours,errors=run_dna(selected)

if errors:
    with st.expander("Note download"):
        for e in errors: st.write("•",e)
if events.empty: st.error("Nessun dato."); st.stop()

st.metric("Incroci analizzati",f"{len(events):,}")

st.subheader("1. Zone Stochastic")
z=zones[zones["Signals"]>=5].sort_values(["Error15 %","Signals"],ascending=[True,False])
st.dataframe(z.style.format({"Signals/day":"{:.2f}","Win15 %":"{:.1f}","Error15 %":"{:.1f}",
                             "Win30 %":"{:.1f}","Error30 %":"{:.1f}","Move15_pct":"{:.3f}",
                             "Median_ADX":"{:.1f}","Median_ATR_pct":"{:.3f}"}),
             use_container_width=True,height=620)

st.subheader("2. Fasce orarie")
hh=hours[hours["Signals"]>=5].sort_values(["Error15 %","Signals"],ascending=[True,False])
st.dataframe(hh,use_container_width=True,height=500)

st.subheader("3. Tutti gli incroci — dataset DNA")
st.dataframe(events,use_container_width=True,height=500)

c1,c2,c3=st.columns(3)
c1.download_button("⬇ EVENTI DNA",events.to_csv(index=False).encode(),"argo4_test3_events.csv","text/csv",use_container_width=True)
c2.download_button("⬇ ZONE STOCH",zones.to_csv(index=False).encode(),"argo4_test3_zones.csv","text/csv",use_container_width=True)
c3.download_button("⬇ ORARI",hours.to_csv(index=False).encode(),"argo4_test3_hours.csv","text/csv",use_container_width=True)

st.caption("Win/Error misurano solo la direzione a +15/+30m. Costi, spread e slippage non inclusi.")
