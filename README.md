# 🚀 ARGO AI 3.0 RC

Release Candidate dell'assistente tecnico ARGO.

## Funzioni

- scanner automatico della watchlist Yahoo Finance;
- EMA 20/50/200, RSI, MACD e ATR;
- supporti e resistenze;
- Score Struttura, Operabilità, Confidence, Conviction e IQS;
- riconoscimento di breakout, breakout da verificare, pullback e falso breakout;
- piano long con Entry, Stop Loss, TP1, TP2 e rapporto R/R;
- dimensionamento teorico in funzione del capitale e del rischio percentuale;
- grafici interattivi con livelli operativi;
- esportazione CSV.

## Correzioni RC

- eliminato il `TypeError` causato da `.round()` su colonne `object`;
- conversione numerica sicura per valori `None`, `NaN`, stringhe e simboli;
- maggiore tolleranza a dati incompleti e deploy parziali;
- conversione sicura dei livelli inviati ai grafici;
- test automatici del formatter e del Trade Engine.

## Deploy

Caricare tutti i file nella root del repository GitHub e fare commit. Streamlit
ridistribuirà automaticamente l'app.

## Avvertenza

ARGO è uno strumento informativo e sperimentale. Non costituisce consulenza
finanziaria né un ordine di acquisto o vendita. I CFD comportano un rischio
elevato di perdita per effetto della leva.

## ARGO AI 3.1 - Trade Manager
- Sezione Operazioni aperte separata dallo scanner.
- Inserimento manuale/assistito di Entry, Stop, TP1 e TP2.
- Prezzo corrente, P/L %, distanza da SL/TP e stato del piano.
- Chiusura trade e storico operazioni.

### Nota persistenza Streamlit Community Cloud
Le operazioni sono salvate in `trades.json` sul filesystem dell'istanza Streamlit. Resistono ai normali rerun della sessione/app, ma Streamlit Community Cloud puo' ricreare l'istanza durante reboot/redeploy: in quel caso il file locale puo' essere perso. Per persistenza definitiva, la prossima integrazione deve usare un database esterno (es. Supabase).
