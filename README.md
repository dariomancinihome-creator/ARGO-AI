# 🚀 ARGO AI

ARGO AI è una web app Streamlit per analizzare automaticamente una watchlist di mercati tramite dati Yahoo Finance.

## Funzioni

- download automatico dei dati;
- EMA 20, EMA 50 ed EMA 200;
- RSI 14;
- MACD;
- ATR;
- supporto e resistenza recenti;
- score tecnico ARGO da 0 a 100;
- classifica degli asset;
- grafici interattivi;
- esportazione CSV.

## File principali

- `app.py`: interfaccia Streamlit;
- `analysis_engine.py`: motore di analisi;
- `data_loader.py`: download Yahoo Finance;
- `indicators.py`: indicatori tecnici;
- `scoring.py`: punteggio ARGO;
- `charts.py`: grafici Plotly;
- `config.py`: watchlist e impostazioni;
- `requirements.txt`: librerie.

## Pubblicazione su Streamlit Community Cloud

1. Carica tutti i file di questa cartella nel repository GitHub.
2. Apri Streamlit Community Cloud.
3. Accedi tramite GitHub.
4. Crea una nuova app.
5. Seleziona il repository `ARGO-AI`.
6. Branch: `main`.
7. Main file path: `app.py`.
8. Premi `Deploy`.

## Utilizzo quotidiano

Apri il link dell'app e premi **Aggiorna analisi**.

I risultati vengono conservati in cache per circa 15 minuti per evitare download ripetuti inutili.

## Avvertenza

ARGO AI è uno strumento informativo e sperimentale. Non costituisce consulenza finanziaria né un ordine di acquisto o vendita. Le quotazioni Yahoo Finance possono essere ritardate o differire da quelle del broker.
