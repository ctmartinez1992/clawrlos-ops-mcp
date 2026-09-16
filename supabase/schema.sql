-- Run this once in the Supabase SQL editor for your project.
-- The application never runs migrations itself.

create extension if not exists pgcrypto;

create table if not exists news_items (
    id uuid primary key default gen_random_uuid(),
    source text not null,
    external_id text not null,
    title text not null,
    url text,
    summary text,
    score numeric,
    author text,
    extra jsonb not null default '{}'::jsonb,
    fetched_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    unique (source, external_id)
);

create index if not exists news_items_fetched_at_idx on news_items (fetched_at);
create index if not exists news_items_source_idx on news_items (source);
create index if not exists news_items_created_at_idx on news_items (created_at);

-- RLS stays enabled with no policies. The server connects with the
-- service_role key only, which bypasses RLS entirely. Never use the
-- anon key for this project — writes and deletes require bypassing RLS.
alter table news_items enable row level security;
