import streamlit as st
from argo4_backtester import run_test5, XTB

st.set_page_config(page_title="ARGO 4.0 Test 5 XTB",page_icon="💶",layout="wide")
st.title("💶 ARGO 4.0 — Test 5: XTB net edge")
st.caption("BTC + GBP/USD: il segnale conta come WIN solo se supera spread + allowance di slippage.")

st.info(
    "Assunzioni del test: GBP/USD spread 0.00017; BTC spread 0,22% come scenario conservativo. "
    "Slippage simulato: 0,5 bps per lato su GBP/USD e 2 bps per lato su BTC. "
    "Sono ipotesi di backtest, non una garanzia dei costi reali."
)

if not st.button("▶ ESEGUI TEST 5 XTB",type="primary",use_container_width=True):
    st.stop()

with st.spinner("Calcolo edge netto a 15/30/45/60 minuti..."):
    events,summary,errors=run_test5()

if errors:
    with st.expander("Note download"):
        for e in errors: st.write("•",e)
if summary.empty:
    st.error("Nessun evento DNA disponibile."); st.stop()

st.subheader("DNA validati — risultato dopo i costi simulati XTB")
st.dataframe(summary.style.format({
    "Signals/day":"{:.2f}","Avg hurdle %":"{:.3f}",
    "Gross Win 15m %":"{:.1f}","Net Win 15m %":"{:.1f}","Avg net 15m %":"{:.3f}",
    "Gross Win 30m %":"{:.1f}","Net Win 30m %":"{:.1f}","Avg net 30m %":"{:.3f}",
    "Gross Win 45m %":"{:.1f}","Net Win 45m %":"{:.1f}","Avg net 45m %":"{:.3f}",
    "Gross Win 60m %":"{:.1f}","Net Win 60m %":"{:.1f}","Avg net 60m %":"{:.3f}",
}),use_container_width=True)

st.subheader("Singoli segnali")
st.dataframe(events,use_container_width=True,height=600)

c1,c2=st.columns(2)
c1.download_button("⬇ RISULTATI XTB",summary.to_csv(index=False).encode(),
                   "argo4_test5_xtb_summary.csv","text/csv",use_container_width=True)
c2.download_button("⬇ EVENTI XTB",events.to_csv(index=False).encode(),
                   "argo4_test5_xtb_events.csv","text/csv",use_container_width=True)

st.caption("La leva non modifica l'edge percentuale del segnale: amplifica P&L e rischio. "
           "Swap overnight non incluso perché il test è intraday.")
