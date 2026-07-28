# ARGO AI 2.1

Dashboard Streamlit per analisi tecnica automatica.

## Novità 2.1

- Score Struttura separato dallo Score Operabilità
- breakout confermato
- breakout da verificare
- attesa breakout
- pullback da monitorare
- falso breakout semplificato
- controllo RSI, MACD e volumi
- commento dinamico per ogni asset
- supporto e resistenza visualizzati nei grafici

## Aggiornamento

Caricare tutti i file di questo pacchetto nella cartella principale del repository GitHub e confermare il commit. Streamlit aggiornerà automaticamente l'app.

## Avvertenza

ARGO AI è uno strumento informativo e sperimentale. Non costituisce consulenza finanziaria né un ordine di acquisto o vendita.

---

## ARGO Alert Push

Il progetto include un motore automatico che viene eseguito da GitHub Actions ogni 15 minuti circa.
Analizza l'intera watchlist su candele orarie completate, seleziona i cinque asset con la migliore operabilità e invia una notifica Pushover solo quando rileva un **Breakout confermato** con:

- Operabilità almeno 75/100
- Struttura almeno 65/100
- MACD favorevole
- RSI non eccessivo
- Volumi almeno 1,05 volte la media

### GitHub Secrets richiesti

- `PUSHOVER_USER_KEY`
- `PUSHOVER_API_TOKEN`

### Primo test

Aprire **Actions → ARGO Alert Push → Run workflow**, lasciare attiva l'opzione di test e premere **Run workflow**. La notifica di prova conferma esclusivamente il collegamento con Pushover. Gli alert di mercato partono soltanto quando le condizioni tecniche sono soddisfatte.

### Nota operativa

GitHub Actions può avviarsi con alcuni minuti di ritardo rispetto all'orario programmato. I dati Yahoo Finance possono essere ritardati e non coincidono necessariamente con quelli del broker. ARGO è uno strumento informativo e sperimentale, non un sistema di esecuzione automatica.
