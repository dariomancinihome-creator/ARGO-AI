# ARGO 4.0 LAB — M15

Laboratorio quantitativo separato dall'ARGO operativo.

## Come lanciarlo su Streamlit
Temporaneamente imposta il **Main file path** dell'app di test su:

`lab_app.py`

Oppure crea una seconda app Streamlit collegata allo stesso repository e usa `lab_app.py` come entrypoint.

## Cosa testa
- M15, ultimo mese disponibile (~22 sessioni per mercati feriali)
- Stochastic 5-3-3, 8-3-3, 10-5-5
- EMA 9/21 e pendenza EMA9
- ADX14 >= 18 e crescente
- ATR14 sopra il 40° percentile dell'asset
- BUY e SELL separati
- esito a +15m e +30m
- segnali/giorno
- zona Stochastic più efficace
- score bilanciato frequenza/accuratezza/movimento

## Importante
Il laboratorio non invia ordini e non modifica Supabase.
Il risultato serve a scegliere il DNA di ARGO 4.0 Session Trader.
