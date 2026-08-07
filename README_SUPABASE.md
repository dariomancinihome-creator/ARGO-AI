# ARGO AI 3.2 - Supabase Persistence

Questa versione mantiene il Trade Manager della 3.1 e salva le operazioni in Supabase.

## 1. Supabase

Crea/apri il progetto Supabase e nel **SQL Editor** esegui tutto il contenuto di:

`SUPABASE_SETUP.sql`

## 2. Streamlit Secrets

In Streamlit Community Cloud:

**Manage app → Settings → Secrets**

inserisci:

```toml
SUPABASE_URL = "https://TUO-PROGETTO.supabase.co"
SUPABASE_ANON_KEY = "LA_TUA_ANON_KEY"
ARGO_OWNER_ID = "argo-personale"
ARGO_APP_PASSWORD = "scegli-una-password-forte"
```

Non inserire queste chiavi nel codice o su GitHub.

`ARGO_APP_PASSWORD` è fortemente consigliata perché la tua app è pubblica:
senza login, chiunque apra il link può vedere e modificare il Trade Manager.

## 3. GitHub

Carica tutti i file di questo pacchetto nel repository e fai commit.

Messaggio consigliato:

`ARGO AI 3.2 - Supabase Trade Manager`

Streamlit effettuerà il redeploy automaticamente.

## 4. Verifica

Dopo l'accesso, nella sezione Trade Manager deve comparire:

`Archivio Trade Manager: Supabase`

Aggiungi un trade di prova, aggiorna la pagina e verifica che rimanga.
Puoi anche controllare la tabella `argo_trades` dal Table Editor di Supabase.

## Sicurezza

Questa prima integrazione è pensata per un'app personale protetta da password.
La versione multiutente corretta richiederà Supabase Auth e policy RLS basate su `auth.uid()`.
