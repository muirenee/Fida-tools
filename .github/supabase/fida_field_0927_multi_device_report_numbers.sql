-- Fida Field 0.9.27
-- Production migrations applied through Supabase:
--   multi_device_report_number_reservations
--   report_number_local_sequence_floor
--
-- Purpose: reserve workspace-unique service report numbers before the first job upsert.
-- The reservation is idempotent by job UUID, survives client retries, and uses a local
-- sequence floor so collision recovery cannot choose a number already used by another
-- unsynced job on the same device.

create table if not exists public.report_sequences (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  prefix text not null,
  report_year integer not null,
  last_seq bigint not null default 0,
  updated_at timestamptz not null default now(),
  primary key (workspace_id, prefix, report_year)
);

create table if not exists public.report_number_reservations (
  job_id uuid primary key,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  prefix text not null,
  report_year integer not null,
  seq bigint not null,
  report_no text not null,
  created_at timestamptz not null default now(),
  unique (workspace_id, report_no),
  unique (workspace_id, prefix, report_year, seq)
);

-- The deployed RPC signature used by the Android app is:
-- public.reserve_report_number(
--   p_workspace_id uuid,
--   p_job_id uuid,
--   p_requested_report_no text,
--   p_local_max_seq bigint
-- ) returns text
--
-- Authorization is checked with public.is_workspace_member(). Direct table access is
-- revoked from anon/authenticated; authenticated clients receive EXECUTE on the RPC only.
