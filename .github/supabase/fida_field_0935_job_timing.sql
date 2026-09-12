alter table public.jobs add column if not exists service_started_at_ms bigint not null default 0;
alter table public.jobs add column if not exists service_completed_at_ms bigint not null default 0;
alter table public.jobs add column if not exists service_duration_minutes integer not null default 0;

comment on column public.jobs.service_started_at_ms is 'Epoch milliseconds when field service work started; 0 means not tracked.';
comment on column public.jobs.service_completed_at_ms is 'Epoch milliseconds when field service work completed; 0 means not tracked.';
comment on column public.jobs.service_duration_minutes is 'Recorded field service duration in whole minutes; 0 when not tracked or under one minute.';
