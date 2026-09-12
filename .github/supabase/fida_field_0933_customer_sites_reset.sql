-- Fida Field 0.9.33
-- Shared customer sites and Owner-only operational workspace reset.

create table if not exists public.customer_sites (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  customer_id uuid not null references public.customers(id) on delete cascade,
  site_id uuid not null references public.sites(id) on delete cascade,
  active boolean not null default true,
  created_by uuid references auth.users(id) on delete set null,
  updated_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(workspace_id, customer_id, site_id)
);

create index if not exists idx_customer_sites_customer on public.customer_sites(workspace_id, customer_id, active);
create index if not exists idx_customer_sites_site on public.customer_sites(workspace_id, site_id, active);
alter table public.customer_sites enable row level security;

create policy customer_sites_select on public.customer_sites for select to authenticated using (public.is_workspace_member(workspace_id));
create policy customer_sites_insert on public.customer_sites for insert to authenticated with check (
  public.can_manage_workspace(workspace_id)
  and exists (select 1 from public.customers c where c.id=customer_id and c.workspace_id=workspace_id)
  and exists (select 1 from public.sites s where s.id=site_id and s.workspace_id=workspace_id)
);
create policy customer_sites_update on public.customer_sites for update to authenticated using (public.can_manage_workspace(workspace_id)) with check (
  public.can_manage_workspace(workspace_id)
  and exists (select 1 from public.customers c where c.id=customer_id and c.workspace_id=workspace_id)
  and exists (select 1 from public.sites s where s.id=site_id and s.workspace_id=workspace_id)
);
create policy customer_sites_delete on public.customer_sites for delete to authenticated using (public.can_manage_workspace(workspace_id));
grant select, insert, update, delete on public.customer_sites to authenticated;

insert into public.customer_sites(workspace_id, customer_id, site_id, active, created_at, updated_at)
select s.workspace_id, s.customer_id, s.id, true, now(), now()
from public.sites s
where s.customer_id is not null and s.deleted_at is null
on conflict (workspace_id, customer_id, site_id) do update set active=true, updated_at=now();

create table if not exists public.workspace_data_state (
  workspace_id uuid primary key references public.workspaces(id) on delete cascade,
  operational_generation bigint not null default 1 check (operational_generation >= 1),
  last_reset_at timestamptz,
  reset_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default now()
);
alter table public.workspace_data_state enable row level security;
create policy workspace_data_state_select on public.workspace_data_state for select to authenticated using (public.is_workspace_member(workspace_id));
revoke insert, update, delete on public.workspace_data_state from authenticated;
grant select on public.workspace_data_state to authenticated;
insert into public.workspace_data_state(workspace_id, operational_generation) select id,1 from public.workspaces on conflict (workspace_id) do nothing;

create or replace function public.get_workspace_operational_generation(p_workspace_id uuid)
returns bigint language plpgsql security definer set search_path=public,pg_temp as $$
declare v_generation bigint;
begin
  if auth.uid() is null or not public.is_workspace_member(p_workspace_id) then raise exception 'Workspace membership required'; end if;
  insert into public.workspace_data_state(workspace_id,operational_generation) values(p_workspace_id,1) on conflict(workspace_id) do nothing;
  select operational_generation into v_generation from public.workspace_data_state where workspace_id=p_workspace_id;
  return coalesce(v_generation,1);
end; $$;
revoke all on function public.get_workspace_operational_generation(uuid) from public,anon;
grant execute on function public.get_workspace_operational_generation(uuid) to authenticated;

create or replace function public.reset_workspace_operational_data(p_workspace_id uuid)
returns bigint language plpgsql security definer set search_path=public,pg_temp as $$
declare v_uid uuid:=auth.uid(); v_generation bigint;
begin
  if v_uid is null then raise exception 'Authentication required'; end if;
  if not exists(select 1 from public.workspace_members wm where wm.workspace_id=p_workspace_id and wm.user_id=v_uid and wm.role='owner' and wm.status='active') then
    raise exception 'Only the active workspace Owner can reset operational data';
  end if;
  delete from public.report_number_reservations where workspace_id=p_workspace_id;
  delete from public.job_assignment_history where workspace_id=p_workspace_id;
  delete from public.maintenance_logs where workspace_id=p_workspace_id;
  delete from public.job_photos where workspace_id=p_workspace_id;
  delete from public.jobs where workspace_id=p_workspace_id;
  delete from public.assets where workspace_id=p_workspace_id;
  delete from public.customer_sites where workspace_id=p_workspace_id;
  delete from public.sites where workspace_id=p_workspace_id;
  delete from public.customers where workspace_id=p_workspace_id;
  delete from public.report_sequences where workspace_id=p_workspace_id;
  insert into public.workspace_data_state(workspace_id,operational_generation,last_reset_at,reset_by,updated_at)
  values(p_workspace_id,2,now(),v_uid,now())
  on conflict(workspace_id) do update set operational_generation=public.workspace_data_state.operational_generation+1,last_reset_at=now(),reset_by=v_uid,updated_at=now()
  returning operational_generation into v_generation;
  return v_generation;
end; $$;
revoke all on function public.reset_workspace_operational_data(uuid) from public,anon;
grant execute on function public.reset_workspace_operational_data(uuid) to authenticated;
