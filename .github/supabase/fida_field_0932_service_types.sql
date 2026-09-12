-- Fida Field 0.9.32
-- Workspace-managed service checklist templates.
-- Applied to Supabase production project before this source trace was committed.

create table if not exists public.service_checklist_templates (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  template_key text not null,
  name text not null,
  items jsonb not null default '[]'::jsonb,
  sort_order integer not null default 0,
  active boolean not null default true,
  updated_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(workspace_id, template_key),
  constraint service_checklist_templates_key_len check (char_length(template_key) between 1 and 80),
  constraint service_checklist_templates_name_len check (char_length(name) between 1 and 120),
  constraint service_checklist_templates_items_array check (jsonb_typeof(items) = 'array')
);

alter table public.service_checklist_templates enable row level security;

create policy service_checklist_templates_select on public.service_checklist_templates
for select to authenticated using (public.is_workspace_member(workspace_id));

create policy service_checklist_templates_insert on public.service_checklist_templates
for insert to authenticated with check (public.can_manage_workspace(workspace_id));

create policy service_checklist_templates_update on public.service_checklist_templates
for update to authenticated using (public.can_manage_workspace(workspace_id))
with check (public.can_manage_workspace(workspace_id));

create policy service_checklist_templates_delete on public.service_checklist_templates
for delete to authenticated using (public.can_manage_workspace(workspace_id));

grant select, insert, update, delete on public.service_checklist_templates to authenticated;

insert into public.service_checklist_templates(workspace_id,template_key,name,items,sort_order,active)
select w.id,v.template_key,v.name,v.items::jsonb,v.sort_order,true
from public.workspaces w
cross join (values
 ('preventive','Preventive maintenance','["Visual condition inspected","Connections and cabling checked","Equipment cleaned or housekeeping completed","Operational test completed","Alarms and indicators checked","Maintenance findings recorded"]',10),
 ('corrective','Corrective maintenance','["Fault symptoms verified","Fault source isolated","Repair or replacement completed","Connections restored and secured","Operational test completed","Final operating condition verified"]',20),
 ('installation','Installation / commissioning','["Equipment installed or mounted","Power and cabling connected","Configuration completed","Network or service connectivity tested","Functional test completed","Labelling or handover completed"]',30),
 ('inspection','Inspection / site survey','["Physical condition inspected","Power and environment checked","Cabling and connections inspected","Configuration or status reviewed","Findings documented","Recommendations recorded"]',40)
) as v(template_key,name,items,sort_order)
on conflict (workspace_id,template_key) do nothing;
