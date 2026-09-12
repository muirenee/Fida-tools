-- Fida Field 0.9.34
-- Owner/Admin removal of a non-owner workspace person.
-- Removes workspace membership and retires linked field profiles while preserving job history.

create or replace function public.remove_workspace_person(p_workspace_id uuid, p_member_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_actor_role text;
  v_target record;
begin
  select wm.role::text into v_actor_role
  from public.workspace_members wm
  where wm.workspace_id = p_workspace_id
    and wm.user_id = auth.uid()
    and wm.status::text = 'active'
  limit 1;

  if v_actor_role is null or v_actor_role not in ('owner','admin') then
    raise exception 'Owner or Admin access required';
  end if;

  select wm.id, wm.user_id, wm.role::text as role
    into v_target
  from public.workspace_members wm
  where wm.workspace_id = p_workspace_id
    and wm.id = p_member_id
  limit 1;

  if v_target.id is null then
    raise exception 'Workspace member not found';
  end if;
  if v_target.role = 'owner' then
    raise exception 'Workspace owner cannot be deleted';
  end if;
  if v_target.user_id = auth.uid() then
    raise exception 'You cannot delete your own workspace membership here';
  end if;

  update public.technicians
     set active = false,
         deleted_at = coalesce(deleted_at, now()),
         updated_at = now(),
         updated_by = auth.uid()
   where workspace_id = p_workspace_id
     and user_id = v_target.user_id
     and deleted_at is null;

  delete from public.workspace_members
   where workspace_id = p_workspace_id
     and id = p_member_id;

  return jsonb_build_object('ok', true, 'member_id', p_member_id);
end;
$$;

revoke all on function public.remove_workspace_person(uuid,uuid) from public;
grant execute on function public.remove_workspace_person(uuid,uuid) to authenticated;
