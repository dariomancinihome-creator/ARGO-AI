import streamlit as st
from argo4_backtester import UNIVERSE, run_validation

st.set_page_config(
    page_title="ARGO 4.0 Test 4",
    page_icon="🏁",
    layout="wide"
)

st.title("🏁 ARGO 4.0 — Test 4: validazione 70/30")
st.caption(
    "Il primo 70% cronologico scopre il DNA. "
    "L'ultimo 30% lo verifica senza modificare le regole."
)

with st.sidebar:
    defaults = [
        "Gold","Nasdaq 100","Bitcoin","NVIDIA",
        "Tesla","Amazon","EUR/USD","GBP/USD"
    ]

    selected = st.multiselect(
        "Asset",
        list(UNIVERSE),
        default=defaults
    )

    st.markdown("**Training:** primo 70%")
    st.markdown("**Out-of-sample:** ultimo 30%")

    run = st.button(
        "▶ ESEGUI TEST 4",
        type="primary",
        use_container_width=True
    )

if not run:
    st.info("Premi ESEGUI TEST 4.")
    st.stop()

if not selected:
    st.warning("Seleziona almeno un asset.")
    st.stop()

with st.spinner(
    "Scarico M15, scopro le regole sul 70% e le provo sul 30%..."
):
    events, train, test, validated, errors = run_validation(selected)

if errors:
    with st.expander("Note download"):
        for error in errors:
            st.write("•", error)

if validated.empty:
    st.error("Nessuna regola validabile trovata.")
    st.stop()

stable = validated[validated["Stable"] == True]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Incroci totali", len(events))
c2.metric("Training", len(train))
c3.metric("Out-of-sample", len(test))
c4.metric("Regole stabili", len(stable))

st.subheader("🏆 DNA che ha retto fuori campione")

display_cols = [
    "Asset","Stoch","Direction","K zone","EMA state",
    "Train signals","Train Win15 %","Test signals","Test Win15 %",
    "Train Win30 %","Test Win30 %","Win15 degradation pp",
    "Stable","Validation score"
]

st.dataframe(
    stable[display_cols].style.format({
        "Train Win15 %":"{:.1f}",
        "Test Win15 %":"{:.1f}",
        "Train Win30 %":"{:.1f}",
        "Test Win30 %":"{:.1f}",
        "Win15 degradation pp":"{:.1f}",
        "Validation score":"{:.1f}",
    }),
    use_container_width=True,
    height=550
)

st.subheader("Tutte le regole scoperte")

st.dataframe(
    validated[display_cols].style.format({
        "Train Win15 %":"{:.1f}",
        "Test Win15 %":"{:.1f}",
        "Train Win30 %":"{:.1f}",
        "Test Win30 %":"{:.1f}",
        "Win15 degradation pp":"{:.1f}",
        "Validation score":"{:.1f}",
    }),
    use_container_width=True,
    height=650
)

st.download_button(
    "⬇ Scarica validazione CSV",
    validated.to_csv(index=False).encode("utf-8"),
    "argo4_test4_validation.csv",
    "text/csv",
    use_container_width=True,
)

st.caption(
    "Una regola è marcata Stable se ha campione test sufficiente, "
    "Win15 out-of-sample ≥55% e degrado rispetto al training ≤12 punti percentuali. "
    "Spread, slippage, leva e costi non sono inclusi."
)
