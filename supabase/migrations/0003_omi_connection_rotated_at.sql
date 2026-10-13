-- Track the last time an Omi connection token was rotated.
alter table if exists public.omi_connections
  add column if not exists rotated_at double precision;
