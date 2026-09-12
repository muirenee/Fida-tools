from pathlib import Path

main=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
gradle=Path('fida-field/app/build.gradle')
s=main.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'0.9.33 reset UI patch failed: {label}')
    s=s.replace(old,new,1)

old='''    private void confirmResetAllAppData(){
        if(!requireWorkspaceManager("Reset all app data"))return;LinearLayout f=form();f.addView(paragraph("This permanently removes all local customers, sites, assets, jobs, photos, signatures, settings, cached service types and cloud sign-in from this device. Supabase workspace data is NOT deleted. Type RESET to continue."));EditText confirm=input("Type RESET","");f.addView(confirm);AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle("Reset all app data?").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Reset",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(!"RESET".equals(val(confirm))){confirm.setError("Type RESET exactly");return;}dialog.dismiss();performLocalFactoryReset();}));dialog.show();
    }
'''
new='''    private void confirmWorkspaceOperationalReset(){
        if(accountTeam==null||!AccountTeamManager.ROLE_OWNER.equals(accountTeam.accountRole())){new MaterialAlertDialogBuilder(this).setTitle("Workspace Owner only").setMessage("This action is restricted to the workspace Owner.").setPositiveButton("OK",null).show();return;}if(!accountTeam.hasCloudWorkspace()||!cloudSync.signedIn()){new MaterialAlertDialogBuilder(this).setTitle("Cloud workspace required").setMessage("Sign in and connect the cloud workspace first.").setPositiveButton("OK",null).show();return;}
        LinearLayout f=form();f.addView(paragraph("This clears workspace operational records from Supabase and this device: customers, customer/site links, sites, assets, jobs, job photos, signatures, maintenance history and report numbering. Workspace membership, field-person profiles, invitations, subscription/billing, branding, service checklists, AI usage and your account are kept. Other devices will clear stale operational records on their next sync."));EditText confirm=input("Type CONFIRM WORKSPACE RESET","");f.addView(confirm);AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle("Reset workspace operational data?").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Confirm",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(!"CONFIRM WORKSPACE RESET".equals(val(confirm))){confirm.setError("Type CONFIRM WORKSPACE RESET exactly");return;}dialog.dismiss();runCloud("Resetting workspace operational data…",()->cloudSync.resetWorkspaceOperationalData(accountTeam.workspaceId()),obj->{toast("Workspace operational data reset");showDashboard();});}));dialog.show();
    }

    private void confirmResetAllAppData(){
        if(!requireWorkspaceManager("Reset local app data"))return;LinearLayout f=form();f.addView(paragraph("This permanently removes all local customers, sites, assets, jobs, photos, signatures, settings, cached service types and cloud sign-in from this device. Supabase workspace data is NOT deleted. Type RESET to continue."));EditText confirm=input("Type RESET","");f.addView(confirm);AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle("Reset local app data?").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Reset",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(!"RESET".equals(val(confirm))){confirm.setError("Type RESET exactly");return;}dialog.dismiss();performLocalFactoryReset();}));dialog.show();
    }
'''
rep(old,new,'workspace reset dialog')

old='b.addView(section("Data management"));MaterialButton resetData=outlineButton("Reset all app data");resetData.setOnClickListener(v->confirmResetAllAppData());b.addView(resetData);b.addView(paragraph("Reset removes data and settings from this device and signs out. Cloud workspace data is not deleted and can sync back after you sign in again."));'
new='b.addView(section("Data management"));MaterialButton resetData=outlineButton("Reset local app data");resetData.setOnClickListener(v->confirmResetAllAppData());b.addView(resetData);b.addView(paragraph("Local reset affects this device only. Supabase workspace data is kept."));if(accountTeam!=null&&AccountTeamManager.ROLE_OWNER.equals(accountTeam.accountRole())&&accountTeam.hasCloudWorkspace()){MaterialButton workspaceReset=outlineButton("Reset workspace operational data · cloud + local");workspaceReset.setOnClickListener(v->confirmWorkspaceOperationalReset());b.addView(workspaceReset);b.addView(paragraph("Owner-only. Workspace/account, team access, subscription, branding, service checklists and AI usage are preserved."));}'
rep(old,new,'settings reset controls')

rep('Fida Field 0.9.23 Test\\nPeople access enable/disable controls, refined home dashboard and professional service reporting by Fidalix.','Fida Field 0.9.33 Test\\nShared customer sites, customer-filtered job sites and Owner-only operational cloud reset.','about version')
main.write_text(s)

g=gradle.read_text()
if '        versionCode 35\n' not in g or "        versionName '0.9.32-test'\n" not in g:
    raise SystemExit('0.9.33 reset UI patch failed: version markers')
g=g.replace('        versionCode 35\n','        versionCode 36\n',1).replace("        versionName '0.9.32-test'\n","        versionName '0.9.33-test'\n",1)
gradle.write_text(g)
print('Fida Field 0.9.33 reset UI + version patch applied')
