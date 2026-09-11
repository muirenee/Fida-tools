from pathlib import Path


def insert_before_once(text, anchor, addition, marker):
    if marker in text:
        return text
    if anchor not in text:
        raise AssertionError(f"missing anchor for {marker}")
    return text.replace(anchor, addition + anchor, 1)


def replace_range(text, start, end, replacement, marker):
    if marker in text:
        return text
    a = text.find(start)
    if a < 0:
        raise AssertionError(f"missing start anchor for {marker}")
    b = text.find(end, a)
    if b < 0:
        raise AssertionError(f"missing end anchor for {marker}")
    return text[:a] + replacement + text[b:]

# Local invitation cleanup.
p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
s = p.read_text()
anchor = '    public void cancelWorkspaceInvite(long id){ContentValues v=new ContentValues();v.put("status","Cancelled");v.put("updated_at",now());getWritableDatabase().update("workspace_invites",v,"id=?",new String[]{String.valueOf(id)});queueSync("workspace_invite",id,"upsert");}\n'
addition = anchor + '    public int clearCancelledWorkspaceInvites(String workspaceId){return getWritableDatabase().delete("workspace_invites","workspace_id=? AND status=\\\'Cancelled\\\'",new String[]{workspaceId==null?"":workspaceId});}\n'
if 'clearCancelledWorkspaceInvites' not in s:
    if anchor not in s:
        raise AssertionError('missing local invitation cleanup anchor')
    s = s.replace(anchor, addition, 1)
p.write_text(s)

# Cloud RPC wrapper. The backend RPC is deployed separately as a Supabase migration.
p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s = p.read_text()
anchor = '    public void cancelInvite(String inviteId)throws Exception{client.rpc("cancel_workspace_invite",new JSONObject().put("p_invite_id",inviteId));}\n'
addition = anchor + '    public void clearCancelledInvites(String workspaceId)throws Exception{client.rpc("clear_cancelled_workspace_invites",new JSONObject().put("p_workspace_id",workspaceId));}\n'
if 'clearCancelledInvites' not in s:
    if anchor not in s:
        raise AssertionError('missing cloud invitation cleanup anchor')
    s = s.replace(anchor, addition, 1)
p.write_text(s)

# UI: one renderer is shared by People & Team and the legacy Team page.
p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = p.read_text()

# Replace the legacy Team invitation list with the shared renderer.
legacy_start = '        List<AppDatabase.Row> invites=db.workspaceInvites(accountTeam.workspaceId());b.addView(section("Invitations"));'
legacy_end = '\n    }\n\n    private void showInviteDialog()'
if legacy_start in s:
    a = s.index(legacy_start)
    b = s.index(legacy_end, a)
    s = s[:a] + '        renderWorkspaceInvitations(b,cloud);' + s[b:]

# Replace People & Team invitation list with the shared renderer.
people_start = '        if(accountTeam.hasWorkspace()){\n            List<AppDatabase.Row> invites=db.workspaceInvites(accountTeam.workspaceId());b.addView(section("Pending app invitations"));'
people_end = '        }\n    }\n\n    private void showUnifiedPerson'
if people_start in s:
    a = s.index(people_start)
    b = s.index(people_end, a)
    s = s[:a] + '        if(accountTeam.hasWorkspace())renderWorkspaceInvitations(b,cloud);\n    }\n\n' + s[b + len('        }\n    }\n\n'):]

helper_anchor = '    private void showUnifiedPerson(long memberId,long technicianId){\n'
helper = '''    private void renderWorkspaceInvitations(LinearLayout b,boolean cloud){
        List<AppDatabase.Row> all=db.workspaceInvites(accountTeam.workspaceId());ArrayList<AppDatabase.Row> pending=new ArrayList<>(),history=new ArrayList<>();int cancelled=0;
        for(AppDatabase.Row r:all){String status=r.s("status");if("Pending".equalsIgnoreCase(status))pending.add(r);else{history.add(r);if("Cancelled".equalsIgnoreCase(status))cancelled++;}}
        b.addView(section("Pending app invitations ("+pending.size()+")"));
        if(pending.isEmpty())b.addView(empty("No pending invitations."));
        for(AppDatabase.Row r:pending){MaterialCardView c=rowCard(r.s("email"),r.s("role"),"Pending");c.setOnClickListener(v->{String code=r.s("token");MaterialAlertDialogBuilder d=new MaterialAlertDialogBuilder(this).setTitle("Pending invitation").setMessage(r.s("email")+" · "+r.s("role")+(code.isEmpty()?"":"\\n\\nInvitation code:\\n"+code)+(r.s("expires_at").isEmpty()?"":"\\nExpires: "+r.s("expires_at"))).setNegativeButton("Close",null);if(!code.isEmpty())d.setNeutralButton("Copy code",(x,w)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",code));toast("Invitation code copied");});if(accountTeam.canManageTeam())d.setPositiveButton("Cancel invitation",(x,w)->{if(cloud)runCloud("Cancelling invitation…",()->{cloudSync.cancelInvite(r.s("invite_uuid"));cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return null;},z->{toast("Invitation cancelled");showPeopleTeam();});else{db.cancelWorkspaceInvite(r.id());showPeopleTeam();}});d.show();});b.addView(c);}
        b.addView(section("Invitation history ("+history.size()+")"));
        if(history.isEmpty())b.addView(empty("No accepted, cancelled or expired invitations yet."));
        else for(AppDatabase.Row r:history)b.addView(rowCard(r.s("email"),r.s("role"),r.s("status")));
        if(cancelled>0&&accountTeam.canManageTeam()){final int cancelledCount=cancelled;MaterialButton clearCancelled=outlineButton("Clear cancelled ("+cancelledCount+")");clearCancelled.setOnClickListener(v->new MaterialAlertDialogBuilder(this).setTitle("Remove cancelled invitations?").setMessage("This permanently removes "+cancelledCount+" cancelled invitation record"+(cancelledCount==1?"":"s")+". Accepted invitation history is kept.").setNegativeButton("Keep",null).setPositiveButton("Clear",(d,w)->{if(cloud)runCloud("Clearing cancelled invitations…",()->{cloudSync.clearCancelledInvites(accountTeam.workspaceId());cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return null;},z->{toast("Cancelled invitations cleared");showPeopleTeam();});else{int removed=db.clearCancelledWorkspaceInvites(accountTeam.workspaceId());toast(removed+" cancelled invitation"+(removed==1?"":"s")+" cleared");showPeopleTeam();}}).show());b.addView(clearCancelled);}
    }

'''
s = insert_before_once(s, helper_anchor, helper, 'private void renderWorkspaceInvitations')
s = s.replace('Fida Field 0.9.17 Test\\nSimplified invitation onboarding and workspace role security by Fidalix.', 'Fida Field 0.9.19 Test\\nInvitation history cleanup, technician identity reconciliation and workspace role security by Fidalix.')
p.write_text(s)

# Version bump.
p = Path('fida-field/app/build.gradle')
s = p.read_text()
if "versionName '0.9.19-test'" not in s:
    if "versionCode 21" not in s or "versionName '0.9.18-test'" not in s:
        raise AssertionError('unexpected build version before 0.9.19 bump')
    s = s.replace('versionCode 21','versionCode 22',1).replace("versionName '0.9.18-test'","versionName '0.9.19-test'",1)
p.write_text(s)

print('Fida Field 0.9.19 invitation history patch applied')
