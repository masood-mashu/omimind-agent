-- OMIMIND multi-user workspace schema.
-- Run with Supabase migrations. Every application row is owned by auth.users.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  avatar_url text,
  created_at double precision not null default extract(epoch from now()),
  updated_at double precision not null default extract(epoch from now())
);

create table if not exists public.meetings (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  transcript jsonb not null default '[]'::jsonb,
  summary jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.meeting_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  meeting_id uuid references public.meetings(id) on delete cascade,
  session_id text,
  title text not null default 'Untitled meeting',
  status text not null default 'running' check (status in ('running', 'completed', 'failed')),
  provider text,
  execution_source text,
  dossier_json jsonb,
  started_at double precision not null default extract(epoch from now()),
  completed_at double precision,
  error text,
  created_at double precision not null default extract(epoch from now())
);

create table if not exists public.agent_events (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.meeting_runs(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  role text not null,
  event_type text,
  agent_id text,
  status text not null,
  provider text,
  execution_source text,
  started_at double precision,
  completed_at double precision,
  latency_ms numeric,
  input_summary text,
  output jsonb,
  payload_json jsonb,
  error text,
  evidence_ids jsonb not null default '[]'::jsonb,
  created_at double precision not null default extract(epoch from now())
);

create table if not exists public.action_items (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  meeting_id uuid references public.meetings(id) on delete cascade,
  title text not null,
  description text,
  assignee text,
  due_at double precision,
  status text not null default 'open',
  source_event_id uuid references public.agent_events(id) on delete set null,
  metadata jsonb,
  created_at double precision not null default extract(epoch from now()),
  updated_at double precision not null default extract(epoch from now())
);

create table if not exists public.omi_connections (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  omi_user_id text,
  device_label text,
  token_hash text not null unique,
  pairing_code_hash text,
  pairing_expires_at double precision,
  status text not null default 'pairing' check (status in ('pairing', 'active', 'revoked')),
  last_event_at double precision,
  created_at double precision not null default extract(epoch from now()),
  updated_at double precision not null default extract(epoch from now())
);

create table if not exists public.webhook_inbox (
  id uuid primary key default gen_random_uuid(),
  event_key text not null unique,
  owner_id uuid not null references auth.users(id) on delete cascade,
  uid text not null,
  event_id text,
  payload_hash text not null,
  session_id text,
  status text not null default 'processing' check (status in ('processing', 'completed', 'failed')),
  attempt_count integer not null default 1,
  lease_until double precision,
  last_error text,
  payload jsonb,
  received_at double precision not null,
  completed_at double precision,
  unique (owner_id, event_id),
  unique (uid, event_id)
);

create index if not exists meetings_owner_idx on public.meetings(owner_id, created_at desc);
create index if not exists meeting_runs_owner_idx on public.meeting_runs(owner_id, started_at desc);
create index if not exists agent_events_run_idx on public.agent_events(run_id, created_at);
create index if not exists agent_events_owner_idx on public.agent_events(owner_id, created_at desc);
create index if not exists action_items_owner_idx on public.action_items(owner_id, created_at desc);
create index if not exists omi_connections_owner_idx on public.omi_connections(owner_id, created_at desc);
create index if not exists webhook_inbox_owner_event_idx on public.webhook_inbox(owner_id, event_id);

alter table public.profiles enable row level security;
alter table public.meetings enable row level security;
alter table public.meeting_runs enable row level security;
alter table public.agent_events enable row level security;
alter table public.action_items enable row level security;
alter table public.omi_connections enable row level security;
alter table public.webhook_inbox enable row level security;

create policy "profiles are self owned" on public.profiles
  for all to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

create policy "meetings are owner scoped" on public.meetings
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create policy "runs are owner scoped" on public.meeting_runs
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create policy "agent events are owner scoped" on public.agent_events
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create policy "actions are owner scoped" on public.action_items
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create policy "omi connections are owner scoped" on public.omi_connections
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create policy "webhook inbox is owner scoped" on public.webhook_inbox
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)))
  on conflict (id) do nothing;
  return new;
end;
$$;

revoke execute on function public.handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
