-- ARGO AI 3.2 - Supabase persistence
-- Esegui questo script nel SQL Editor del progetto Supabase.

create table if not exists public.argo_trades (
    id text primary key,
    owner_id text not null,
    asset text not null,
    ticker text not null,
    direction text not null default 'LONG',
    entry double precision not null,
    stop_loss double precision,
    tp1 double precision,
    tp2 double precision,
    setup text,
    opened_at timestamptz not null default now(),
    status text not null default 'OPEN'
        check (status in ('OPEN', 'CLOSED')),
    closed_at timestamptz,
    exit_price double precision,
    created_at timestamptz not null default now()
);

create index if not exists argo_trades_owner_status_idx
on public.argo_trades (owner_id, status);

alter table public.argo_trades enable row level security;

-- Questa policy consente all'app server-side Streamlit, che usa l'anon key,
-- di leggere e modificare le righe. La protezione effettiva dell'interfaccia
-- viene data dalla password ARGO_APP_PASSWORD.
-- Per una futura versione multiutente useremo Supabase Auth e policy per user_id.

drop policy if exists "argo anon select" on public.argo_trades;
drop policy if exists "argo anon insert" on public.argo_trades;
drop policy if exists "argo anon update" on public.argo_trades;

create policy "argo anon select"
on public.argo_trades for select
to anon
using (true);

create policy "argo anon insert"
on public.argo_trades for insert
to anon
with check (true);

create policy "argo anon update"
on public.argo_trades for update
to anon
using (true)
with check (true);
