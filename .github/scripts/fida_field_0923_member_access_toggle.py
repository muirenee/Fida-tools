from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = p.read_text()

# Make app-access state visible directly in the unified People list.
s = replace_once(
    s,
    'String detail=tech.id()>0?(tech.s("role").isEmpty()?"Field technician":tech.s("role"))+(tech.s("phone").isEmpty()?"":" • "+tech.s("phone")):(m.s("email").isEmpty()?"Workspace member":m.s("email"));MaterialCardView c=rowCard(m.s("name"),detail,m.s("role")+" · "+field);',
    'String detail=tech.id()>0?(tech.s("role").isEmpty()?"Field technician":tech.s("role"))+(tech.s("phone").isEmpty()?"":" • "+tech.s("phone")):(m.s("email").isEmpty()?"Workspace member":m.s("email"));String appState="Active".equalsIgnoreCase(m.s("status"))?"App active":"App disabled";MaterialCardView c=rowCard(m.s("name"),detail,m.s("role")+" · "+appState+" · "+field);',
    'people list app status')

old_unified = '''    private void showUnifiedPerson(long memberId,long technicianId){
        if(!requireWorkspaceManager("People & Team"))return;
        AppDatabase.Row member=memberId>0?db.getWorkspaceMember(memberId):new AppDatabase.Row();AppDatabase.Row tech=technicianId>0?db.getTechnician(technicianId):new AppDatabase.Row();boolean hasMember=member.id()>0,hasTech=tech.id()>0;
        LinearLayout f=form();String personName=hasTech?tech.s("name"):member.s("name");String personEmail=hasTech&&!tech.s("email").isEmpty()?tech.s("email"):member.s("email");EditText name=input("Person name *",personName);EditText fieldRole=input("Field role / job title",hasTech?tech.s("role"):"");EditText phone=input("Phone",hasTech?tech.s("phone"):"");EditText email=input("Email",personEmail);MaterialSwitch field=new MaterialSwitch(this);field.setText("Available for field job assignment");field.setChecked(hasTech&&tech.i("active")==1);f.addView(name);f.addView(fieldRole);f.addView(phone);f.addView(email);f.addView(field);
        if(hasMember){f.addView(section("Workspace access"));f.addView(info("Access role",member.s("role")));f.addView(info("Access status",member.s("status")));if(accountTeam.canManageTeam()&&!"Owner".equals(member.s("role"))){MaterialButton access=outlineButton("Manage workspace access");access.setOnClickListener(v->showMemberDialog(memberId));f.addView(access);}}
        if(!hasMember&&hasTech&&accountTeam.hasWorkspace()&&accountTeam.canManageTeam()){f.addView(section("App access"));List<AppDatabase.Row> linkable=db.unlinkedWorkspaceMembers(accountTeam.workspaceId());if(!linkable.isEmpty()){MaterialButton link=outlineButton("Link existing workspace member");link.setOnClickListener(v->showLinkMemberDialog(technicianId));f.addView(link);}MaterialButton invite=outlineButton("Invite this person to workspace");invite.setEnabled(!val(email).isEmpty());invite.setOnClickListener(v->showInviteDialog(val(email),AccountTeamManager.ROLE_TECHNICIAN));f.addView(invite);}
        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle(hasMember||hasTech?"Person profile":"Add field-only person").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Name required");return;}if(!val(email).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(email)).matches()){email.setError("Enter a valid email");return;}String user=hasMember?member.s("user_uuid"):tech.s("user_uuid");if(field.isChecked()||hasTech){db.saveTechnician(technicianId,AppDatabase.map("name",val(name),"role",val(fieldRole),"phone",val(phone),"email",val(email),"user_uuid",user,"active",field.isChecked()?"1":"0"));}d.dismiss();toast(field.isChecked()?"Person available for field jobs":"Person profile saved");showPeopleTeam();}));d.show();
    }
'''
new_unified = '''    private void showUnifiedPerson(long memberId,long technicianId){
        if(!requireWorkspaceManager("People & Team"))return;
        AppDatabase.Row member=memberId>0?db.getWorkspaceMember(memberId):new AppDatabase.Row();AppDatabase.Row tech=technicianId>0?db.getTechnician(technicianId):new AppDatabase.Row();boolean hasMember=member.id()>0,hasTech=tech.id()>0;
        LinearLayout f=form();String personName=hasTech?tech.s("name"):member.s("name");String personEmail=hasTech&&!tech.s("email").isEmpty()?tech.s("email"):member.s("email");EditText name=input("Person name *",personName);EditText fieldRole=input("Field role / job title",hasTech?tech.s("role"):"");EditText phone=input("Phone",hasTech?tech.s("phone"):"");EditText email=input("Email",personEmail);MaterialSwitch field=new MaterialSwitch(this);field.setText("Available for field job assignment");field.setChecked(hasTech&&tech.i("active")==1);f.addView(name);f.addView(fieldRole);f.addView(phone);f.addView(email);f.addView(field);
        final MaterialSwitch appAccess=hasMember&&accountTeam.canManageTeam()&&!"Owner".equals(member.s("role"))?new MaterialSwitch(this):null;
        if(hasMember){f.addView(section("Workspace access"));f.addView(info("Access role",member.s("role")));if(appAccess!=null){appAccess.setText("Workspace app access enabled");appAccess.setChecked("Active".equalsIgnoreCase(member.s("status")));f.addView(appAccess);f.addView(paragraph("Turn this off to suspend this member's workspace access without deleting their account, service history or assignments. It can be enabled again later."));MaterialButton access=outlineButton("Change access role");access.setOnClickListener(v->showMemberDialog(memberId));f.addView(access);}else f.addView(info("Access status",member.s("status")));}
        if(!hasMember&&hasTech&&accountTeam.hasWorkspace()&&accountTeam.canManageTeam()){f.addView(section("App access"));List<AppDatabase.Row> linkable=db.unlinkedWorkspaceMembers(accountTeam.workspaceId());if(!linkable.isEmpty()){MaterialButton link=outlineButton("Link existing workspace member");link.setOnClickListener(v->showLinkMemberDialog(technicianId));f.addView(link);}MaterialButton invite=outlineButton("Invite this person to workspace");invite.setEnabled(!val(email).isEmpty());invite.setOnClickListener(v->showInviteDialog(val(email),AccountTeamManager.ROLE_TECHNICIAN));f.addView(invite);}
        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle(hasMember||hasTech?"Person profile":"Add field-only person").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Name required");return;}if(!val(email).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(email)).matches()){email.setError("Enter a valid email");return;}String n=val(name),fr=val(fieldRole),ph=val(phone),em=val(email),user=hasMember?member.s("user_uuid"):tech.s("user_uuid");boolean fieldEnabled=field.isChecked();Runnable finish=()->{if(fieldEnabled||hasTech)db.saveTechnician(technicianId,AppDatabase.map("name",n,"role",fr,"phone",ph,"email",em,"user_uuid",user,"active",fieldEnabled?"1":"0"));d.dismiss();toast(fieldEnabled?"Person available for field jobs":"Person profile saved");showPeopleTeam();};if(appAccess!=null){String desired=appAccess.isChecked()?"Active":"Inactive";if(!desired.equalsIgnoreCase(member.s("status"))){Runnable change=()->updateWorkspaceMemberAccess(member,member.s("role"),desired,finish);if("Inactive".equals(desired)){new MaterialAlertDialogBuilder(this).setTitle("Disable workspace access?").setMessage(member.s("name")+" will no longer be able to access or synchronize this workspace. Existing jobs, history and the member record are kept, and access can be enabled again later.").setNegativeButton("Keep enabled",null).setPositiveButton("Disable",(a,w)->change.run()).show();}else change.run();return;}}finish.run();}));d.show();
    }
'''
s = replace_once(s, old_unified, new_unified, 'unified person access toggle')

old_member = '''    private void showMemberDialog(long id){
        if(!requireWorkspaceManager("Team administration"))return;
        AppDatabase.Row r=db.getWorkspaceMember(id);if(r.id()==0)return;if("Owner".equals(r.s("role"))){toast("The workspace owner cannot be changed here");return;}LinearLayout f=form();EditText name=input("Name",r.s("name"));EditText email=input("Email",r.s("email"));name.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));email.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});setSpinner(role,r.s("role"));Spinner status=spinner(new String[]{"Active","Inactive"});setSpinner(status,r.s("status"));f.addView(name);f.addView(email);f.addView(label("Role"));f.addView(role);f.addView(label("Status"));f.addView(status);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Edit member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String rr=String.valueOf(role.getSelectedItem()),ss=String.valueOf(status.getSelectedItem());if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){runCloud("Updating member…",()->{cloudSync.updateMember(accountTeam.workspaceId(),r.s("member_uuid"),rr,ss);cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{d.dismiss();toast("Member updated");showPeopleTeam();});}else{if(val(name).isEmpty()){name.setError("Name required");return;}db.saveWorkspaceMember(id,accountTeam.workspaceId(),val(name),val(email),rr,ss);d.dismiss();toast("Member updated");showPeopleTeam();}}));d.show();
    }
'''
new_member = '''    private void showMemberDialog(long id){
        if(!requireWorkspaceManager("Team administration"))return;
        AppDatabase.Row r=db.getWorkspaceMember(id);if(r.id()==0)return;if("Owner".equals(r.s("role"))){toast("The workspace owner cannot be disabled or changed here");return;}LinearLayout f=form();EditText name=input("Name",r.s("name"));EditText email=input("Email",r.s("email"));name.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));email.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});setSpinner(role,r.s("role"));MaterialSwitch enabled=new MaterialSwitch(this);enabled.setText("Workspace app access enabled");enabled.setChecked("Active".equalsIgnoreCase(r.s("status")));f.addView(name);f.addView(email);f.addView(label("Role"));f.addView(role);f.addView(section("Access"));f.addView(enabled);f.addView(paragraph("Disabled members keep their account and history but cannot access or synchronize this workspace until re-enabled."));AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Workspace member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Name required");return;}String rr=String.valueOf(role.getSelectedItem()),ss=enabled.isChecked()?"Active":"Inactive";Runnable save=()->updateWorkspaceMemberAccess(r,rr,ss,()->{d.dismiss();toast(enabled.isChecked()?"Member enabled":"Member disabled");showPeopleTeam();});if(!enabled.isChecked()&&!"Inactive".equalsIgnoreCase(r.s("status"))){new MaterialAlertDialogBuilder(this).setTitle("Disable workspace access?").setMessage(r.s("name")+" will no longer be able to access or synchronize this workspace. Existing jobs and history are not deleted.").setNegativeButton("Keep enabled",null).setPositiveButton("Disable",(a,w)->save.run()).show();}else save.run();}));d.show();
    }

    private void updateWorkspaceMemberAccess(AppDatabase.Row member,String role,String status,Runnable success){
        if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){runCloud("Updating workspace access…",()->{cloudSync.updateMember(accountTeam.workspaceId(),member.s("member_uuid"),role,status);cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->success.run());}
        else{db.saveWorkspaceMember(member.id(),accountTeam.workspaceId(),member.s("name"),member.s("email"),role,status);success.run();}
    }
'''
s = replace_once(s, old_member, new_member, 'member access toggle dialog')

s = replace_once(
    s,
    'b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.22 Test\\nRefined home dashboard, consistent customer terminology, professional reports and customer email delivery by Fidalix."));',
    'b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.23 Test\\nPeople access enable/disable controls, refined home dashboard and professional service reporting by Fidalix."));',
    'about version')

p.write_text(s)

p = Path('fida-field/app/build.gradle')
s = p.read_text()
s = replace_once(s, "        versionCode 25\n        versionName '0.9.22-test'\n", "        versionCode 26\n        versionName '0.9.23-test'\n", 'version bump')
p.write_text(s)
