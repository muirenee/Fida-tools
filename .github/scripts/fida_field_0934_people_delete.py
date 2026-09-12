from pathlib import Path

ROOT = Path('fida-field')
MAIN = ROOT / 'app/src/main/java/com/fidalix/fidafield/MainActivity.java'
DB = ROOT / 'app/src/main/java/com/fidalix/fidafield/AppDatabase.java'
CLOUD = ROOT / 'app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java'
GRADLE = ROOT / 'app/build.gradle'


def replace_once(path: Path, old: str, new: str):
    s = path.read_text()
    if old not in s:
        raise SystemExit(f'Anchor not found in {path}: {old[:100]!r}')
    path.write_text(s.replace(old, new, 1))


# Version bump.
replace_once(GRADLE, 'versionCode 36', 'versionCode 37')
replace_once(GRADLE, "versionName '0.9.33-test'", "versionName '0.9.34-test'")

# Local safe person removal. Historical job/person names remain, but active assignment links are cleared.
db_anchor = '    public void linkTechnicianToMember(long technicianId,long memberId){\n'
db_insert = '''    public void deletePersonTechnician(long technicianId){
        if(technicianId<=0)return;Row tech=getTechnician(technicianId);if(tech.id()==0)return;SQLiteDatabase d=getWritableDatabase();d.beginTransaction();
        try{
            for(Row j:rows("SELECT id FROM jobs WHERE technician_id=?",new String[]{String.valueOf(technicianId)})){ContentValues v=new ContentValues();v.putNull("technician_id");d.update("jobs",v,"id=?",new String[]{String.valueOf(j.id())});queueSync("job",j.id(),"upsert");}
            ContentValues from=new ContentValues();from.putNull("from_technician_id");d.update("job_assignment_history",from,"from_technician_id=?",new String[]{String.valueOf(technicianId)});ContentValues to=new ContentValues();to.putNull("to_technician_id");d.update("job_assignment_history",to,"to_technician_id=?",new String[]{String.valueOf(technicianId)});
            queueSync("technician",technicianId,"delete");d.delete("sync_conflicts","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(technicianId)});d.delete("technicians","id=?",new String[]{String.valueOf(technicianId)});d.setTransactionSuccessful();
        }finally{d.endTransaction();}
    }
    public void deleteWorkspaceMemberLocal(long memberId){if(memberId<=0)return;getWritableDatabase().delete("workspace_members","id=?",new String[]{String.valueOf(memberId)});}

'''
replace_once(DB, db_anchor, db_insert + db_anchor)

# Cloud RPC wrapper.
cloud_anchor = '    public void refreshTeamCache(String workspaceId,boolean canManage)throws Exception{\n'
cloud_insert = '''    public void removeWorkspacePerson(String workspaceId,String memberId)throws Exception{
        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.trim().isEmpty())throw new Exception("Cloud workspace is not bound");if(memberId==null||memberId.trim().isEmpty())throw new Exception("Workspace member ID is missing");
        client.rpc("remove_workspace_person",new JSONObject().put("p_workspace_id",workspaceId.trim()).put("p_member_id",memberId.trim()));
    }

'''
replace_once(CLOUD, cloud_anchor, cloud_insert + cloud_anchor)

# Add a guarded delete action to the unified person profile.
ui_anchor = '        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle(hasMember||hasTech?"Person profile":"Add field-only person").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();\n'
ui_insert = '''        boolean ownerPerson=hasMember&&"Owner".equals(member.s("role"));boolean selfPerson=hasMember&&!member.s("user_uuid").isEmpty()&&member.s("user_uuid").equals(currentJobUserUuid());
        if((hasMember||hasTech)&&!ownerPerson&&!selfPerson){f.addView(section("Danger zone"));MaterialButton deletePerson=outlineButton(hasMember?"Delete person from workspace":"Delete person");deletePerson.setOnClickListener(v->confirmDeletePerson(memberId,technicianId));f.addView(deletePerson);f.addView(paragraph(hasMember?"Deletes this person's workspace membership and field profile. Their login account itself is not deleted.":"Deletes this field-only person. Existing service history is preserved."));}
        else if(ownerPerson)f.addView(paragraph("The workspace Owner cannot be deleted."));else if(selfPerson)f.addView(paragraph("You cannot delete your own workspace membership from People & Team."));
'''
replace_once(MAIN, ui_anchor, ui_insert + ui_anchor)

method_anchor = '    private void showLinkMemberDialog(long technicianId){\n'
method_insert = '''    private void confirmDeletePerson(long memberId,long technicianId){
        AppDatabase.Row member=memberId>0?db.getWorkspaceMember(memberId):new AppDatabase.Row();AppDatabase.Row tech=technicianId>0?db.getTechnician(technicianId):new AppDatabase.Row();boolean hasMember=member.id()>0;String person=!tech.s("name").isEmpty()?tech.s("name"):member.s("name");if(person.isEmpty())person="This person";
        if(hasMember&&"Owner".equals(member.s("role"))){toast("Workspace Owner cannot be deleted");return;}if(hasMember&&!member.s("user_uuid").isEmpty()&&member.s("user_uuid").equals(currentJobUserUuid())){toast("You cannot delete your own workspace membership here");return;}
        String message=hasMember?"This removes "+person+" from the workspace and from future field assignment. Their sign-in account itself is not deleted. Existing job reports keep the recorded technician name and history.":"This removes "+person+" from People & Team and from future field assignment. Existing job reports keep the recorded technician name and history.";
        new MaterialAlertDialogBuilder(this).setTitle("Delete person?").setMessage(message).setNegativeButton("Cancel",null).setPositiveButton("Delete person",(d,w)->performDeletePerson(memberId,technicianId)).show();
    }

    private void performDeletePerson(long memberId,long technicianId){
        AppDatabase.Row member=memberId>0?db.getWorkspaceMember(memberId):new AppDatabase.Row();boolean hasMember=member.id()>0;
        if(hasMember&&accountTeam.hasCloudWorkspace()){
            if(!cloudSync.signedIn()){new MaterialAlertDialogBuilder(this).setTitle("Cloud sign-in required").setMessage("This person has workspace app access. Sign in before deleting them so access is removed from Supabase as well.").setPositiveButton("OK",null).show();return;}
            String remoteMemberId=member.s("member_uuid");runCloud("Deleting person…",()->{cloudSync.removeWorkspacePerson(accountTeam.workspaceId(),remoteMemberId);if(technicianId>0)db.deletePersonTechnician(technicianId);db.deleteWorkspaceMemberLocal(memberId);cloudSync.syncNow(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{toast("Person deleted · history preserved");showPeopleTeam();});return;
        }
        if(technicianId>0)db.deletePersonTechnician(technicianId);if(memberId>0)db.deleteWorkspaceMemberLocal(memberId);toast("Person deleted · history preserved");showPeopleTeam();
    }

'''
replace_once(MAIN, method_anchor, method_insert + method_anchor)

# Keep the About label current.
s = MAIN.read_text()
s = s.replace('Fida Field 0.9.23 Test\\nPeople access enable/disable controls, refined home dashboard and professional service reporting by Fidalix.', 'Fida Field 0.9.34 Test\\nPeople removal, shared customer sites, operational reset and professional service reporting by Fidalix.')
MAIN.write_text(s)

print('Applied Fida Field 0.9.34 People deletion patch')
