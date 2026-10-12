-- Runtime compatibility fixes for the application adapters.
-- This migration is safe to run after 0001 or against an earlier local inbox.

alter table if exists public.webhook_inbox
  add column if not exists payload jsonb,
  add column if not exists lease_until double precision,
  add column if not exists completed_at double precision;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'webhook_inbox' and column_name = 'payload_json'
  ) then
    execute 'update public.webhook_inbox set payload = coalesce(payload, payload_json)';
    alter table public.webhook_inbox drop column payload_json;
  end if;
end $$;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'webhook_inbox'
      and column_name = 'lease_until' and data_type = 'timestamp with time zone'
  ) then
    alter table public.webhook_inbox
      alter column lease_until type double precision
      using extract(epoch from lease_until);
  end if;
end $$;

alter table if exists public.action_items
  add column if not exists metadata jsonb;

create index if not exists webhook_inbox_owner_status_idx
  on public.webhook_inbox(owner_id, status, received_at);
