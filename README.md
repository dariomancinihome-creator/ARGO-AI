# ARGO AI 3.0 Beta

Decision engine personale in Streamlit.

## Funzioni
- EMA 20/50/200, RSI, MACD, ATR, supporti e resistenze
- Confidence, Conviction e Indice Qualità Setup (IQS)
- identificazione breakout, pullback e falsi breakout
- piano operativo long per breakout confermati
- Entry, Stop Loss, TP1, TP2, R/R e dimensionamento teorico della posizione
- comando **ENTRA** soltanto quando tutti i filtri Beta risultano validi

## Regole del piano Beta
- Entry: chiusura della candela di breakout
- Stop: sotto minimo candela/livello rotto con buffer 0,5 ATR
- TP1: 2R
- TP2: resistenza superiore utile (almeno 2,5R), altrimenti 3R
- autorizzazione: Confidence >= 90, volume >= 1,05x, RSI 50-72, stop coerente, R/R >= 2

## Avvio
```bash
pip install -r requirements.txt
streamlit run app.py
```

Strumento sperimentale e informativo; non costituisce consulenza finanziaria né ordine di investimento.
