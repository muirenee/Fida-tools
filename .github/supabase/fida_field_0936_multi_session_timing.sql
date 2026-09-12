alter table public.jobs add column if not exists service_sessions jsonb not null default '[]'::jsonb;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'jobs_service_sessions_is_array'
  ) then
    alter table public.jobs add constraint jobs_service_sessions_is_array check (jsonb_typeof(service_sessions) = 'array');
  end if;
end $$;

update public.jobs
set service_sessions = jsonb_build_array(
  jsonb_build_object(
    'id', gen_random_uuid()::text,
    'started_at_ms', service_started_at_ms,
    'ended_at_ms', coalesce(service_completed_at_ms, 0)
  )
)
where coalesce(service_started_at_ms,0) > 0
  and jsonb_array_length(service_sessions) = 0;
