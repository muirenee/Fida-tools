from pathlib import Path

GRADLE=Path('fida-field/app/build.gradle')
MAIN=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
RESET=Path('fida-field/app/src/main/java/com/fidalix/fidafield/PasswordResetActivity.java')


def replace_once(path:Path,old:str,new:str):
    text=path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:220]!r}')
    path.write_text(text.replace(old,new,1))

replace_once(GRADLE,"versionCode 49\n        versionName '0.9.46-test'","versionCode 50\n        versionName '0.9.47-test'")

replace_once(
    MAIN,
    '    private boolean mainTabScreen=true;\n',
    '    private boolean mainTabScreen=true;\n    private boolean firstRunFlow=false;\n'
)

replace_once(
    MAIN,
    '        if(captureWorkspaceInviteIntent(getIntent())||hasPendingWorkspaceInvite())showAccountWorkspace();else showDashboard();\n',
    '        if(captureWorkspaceInviteIntent(getIntent())||hasPendingWorkspaceInvite())showAccountWorkspace();else if(shouldShowFirstRunWelcome())showFirstRunWelcome();else showDashboard();\n'
)

replace_once(
    MAIN,
    '    private void clearPendingWorkspaceInvite(){prefs.edit().remove(KEY_PENDING_INVITE_TOKEN).remove(KEY_PENDING_INVITE_EMAIL).remove(KEY_PENDING_INVITE_WORKSPACE).remove(KEY_PENDING_INVITE_ROLE).remove(KEY_PENDING_INVITE_EXPIRES).apply();}\n',
    '''    private void clearPendingWorkspaceInvite(){prefs.edit().remove(KEY_PENDING_INVITE_TOKEN).remove(KEY_PENDING_INVITE_EMAIL).remove(KEY_PENDING_INVITE_WORKSPACE).remove(KEY_PENDING_INVITE_ROLE).remove(KEY_PENDING_INVITE_EXPIRES).apply();}\n    private static final String KEY_FIRST_RUN_COMPLETE="first_run_complete";\n    private boolean shouldShowFirstRunWelcome(){\n        if(prefs.getBoolean(KEY_FIRST_RUN_COMPLETE,false)||hasPendingWorkspaceInvite()||accountTeam.hasWorkspace()||cloudSync.signedIn())return false;\n        long existing=db.count("customers",null,null)+db.count("sites",null,null)+db.count("assets",null,null)+db.count("jobs",null,null)+db.count("technicians",null,null);\n        if(existing>0){prefs.edit().putBoolean(KEY_FIRST_RUN_COMPLETE,true).apply();return false;}return true;\n    }\n    private void completeFirstRun(){firstRunFlow=false;prefs.edit().putBoolean(KEY_FIRST_RUN_COMPLETE,true).apply();}\n'''
)

replace_once(
    MAIN,
    '    private void showDashboard(){\n',
    '    private void showDashboard(){\n        if(bottom!=null)bottom.setVisibility(View.VISIBLE);\n'
)

insert=r'''    private void showFirstRunWelcome(){
        firstRunFlow=true;if(bottom!=null)bottom.setVisibility(View.GONE);mainTabScreen=false;setHeader("Welcome to Fida Field","Choose how you want to get started");clear();LinearLayout b=body(page());
        b.addView(heroCard("Service work, organized from day one","Fida Field can work as a shared company workspace across devices or stay completely local on this phone. Choose the setup that matches how you work."));
        b.addView(section("Recommended for teams"));MaterialButton join=button("Join or sign in to my company workspace");join.setOnClickListener(v->showAccountWorkspace());b.addView(join);b.addView(paragraph("Use an invitation link/code from your company, or sign in to an existing Fida Field account on a new device."));
        MaterialButton create=outlineButton("Create a company workspace");create.setOnClickListener(v->showCreateWorkspaceOnboarding());b.addView(create);b.addView(paragraph("Start as the workspace Owner. You can connect cloud sync and invite your team after the company profile is created."));
        b.addView(section("Single-device / offline"));MaterialButton local=outlineButton("Use Fida Field locally");local.setOnClickListener(v->{completeFirstRun();toast("Local mode selected · cloud can be connected later");showDashboard();});b.addView(local);b.addView(paragraph("No sign-in is required. Your data stays on this device until you choose to connect a cloud workspace later from More → Account & Workspace."));
    }

    private void showCreateWorkspaceOnboarding(){
        firstRunFlow=true;if(bottom!=null)bottom.setVisibility(View.GONE);mainTabScreen=false;setHeader("Create company workspace","Owner setup");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Welcome");back.setOnClickListener(v->showFirstRunWelcome());b.addView(back);
        b.addView(heroCard("Set up your company","Create the workspace profile first. You can start locally immediately, then connect cloud sync when you are ready to invite other users or use multiple devices."));
        EditText workspace=input("Company / workspace name *",prefs.getString("company_name",""));EditText person=input("Your name *",prefs.getString("technician_name",""));EditText email=input("Work email",prefs.getString("company_email",""));b.addView(workspace);b.addView(person);b.addView(email);
        MaterialButton create=button("Create workspace");create.setOnClickListener(v->{String w=val(workspace),n=val(person),e=val(email);if(w.isEmpty()){workspace.setError("Workspace name required");return;}if(n.isEmpty()){person.setError("Your name required");return;}if(!e.isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Enter a valid email");return;}accountTeam.saveOwnerWorkspace(w,n,e);prefs.edit().putString("company_name",w).putString("technician_name",n).putString("company_email",e).apply();completeFirstRun();showLocalWorkspaceReady();});b.addView(create);
    }

    private void showLocalWorkspaceReady(){
        if(bottom!=null)bottom.setVisibility(View.GONE);mainTabScreen=false;setHeader("Workspace ready",accountTeam.workspaceName());clear();LinearLayout b=body(page());b.addView(heroCard("Your workspace is ready","The company profile is created on this device. You can begin field work now or connect a Fida Field cloud account for team access, invitations and multi-device synchronization."));b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Your role",accountTeam.accountRole()));
        if(cloudSync.backendConfigured()){MaterialButton cloud=button("Connect cloud & team");cloud.setOnClickListener(v->showAccountWorkspace());b.addView(cloud);}MaterialButton start=outlineButton("Start using Fida Field");start.setOnClickListener(v->showDashboard());b.addView(start);
    }

    private void addPasswordVisibility(LinearLayout host,EditText... fields){
        MaterialSwitch show=new MaterialSwitch(this);show.setText("Show password");show.setOnCheckedChangeListener((button,checked)->{for(EditText field:fields){if(field==null)continue;int at=field.getSelectionStart();field.setTransformationMethod(checked?android.text.method.HideReturnsTransformationMethod.getInstance():android.text.method.PasswordTransformationMethod.getInstance());if(at>=0&&at<=field.length())field.setSelection(at);}});host.addView(show);
    }

    private void showCreateCloudAccountDialog(String suggestedName,String suggestedEmail){
        LinearLayout f=form();f.addView(paragraph("Create your personal Fida Field account. Your company workspace is separate from your account and can be created or joined after sign-in."));EditText name=input("Your name *",suggestedName==null?"":suggestedName);EditText email=input("Email *",suggestedEmail==null?"":suggestedEmail);EditText password=input("Create password","");password.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);EditText confirm=input("Confirm password","");confirm.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);f.addView(name);f.addView(email);f.addView(password);f.addView(confirm);addPasswordVisibility(f,password,confirm);
        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Create Fida Field account").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Create account",null).create();d.setCanceledOnTouchOutside(false);d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String n=val(name),e=val(email),p=val(password),c=val(confirm);if(n.isEmpty()){name.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(p.length()<8){password.setError("Use at least 8 characters");return;}if(!p.equals(c)){confirm.setError("Passwords do not match");return;}runCloud("Creating account…",()->cloudSync.signUp(n,e,p),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);d.dismiss();if(ar.signedIn){toast("Account created and signed in");showAccountWorkspace();}else new MaterialAlertDialogBuilder(this).setTitle("Confirm your email").setMessage("Your account is ready. Open the confirmation email, confirm the address, then return to Fida Field and sign in with the same password.").setPositiveButton("OK",(a,w)->showAccountWorkspace()).show();});}));d.show();
    }

    private void showWorkspaceReady(CloudSyncFoundation.WorkspaceMembership wm,CloudSyncFoundation.SyncResult sync){
        completeFirstRun();if(bottom!=null)bottom.setVisibility(View.GONE);mainTabScreen=false;setHeader("Workspace ready",wm.name);clear();LinearLayout b=body(page());b.addView(heroCard("You're connected to "+wm.name,"Your account and company workspace are now linked on this device. Fida Field completed the first workspace load and is ready for normal use."));b.addView(info("Account",cloudSync.accountEmail()));b.addView(info("Workspace",wm.name));b.addView(info("Your role",wm.role));if(sync!=null){b.addView(info("First sync",sync.message));b.addView(info("Received from workspace",String.valueOf(sync.pulled)));b.addView(info("Sent from this device",String.valueOf(sync.pushed)));}
        MaterialButton start=button("Start using Fida Field");start.setOnClickListener(v->showDashboard());b.addView(start);if(AccountTeamManager.ROLE_OWNER.equals(wm.role)||AccountTeamManager.ROLE_ADMIN.equals(wm.role)){MaterialButton people=outlineButton("Open People & Team");people.setOnClickListener(v->{if(bottom!=null)bottom.setVisibility(View.VISIBLE);showPeopleTeam();});b.addView(people);}
    }

'''
replace_once(MAIN,'    private void showPendingInviteOnboarding(LinearLayout b){',insert+'    private void showPendingInviteOnboarding(LinearLayout b){')

replace_once(MAIN,'        b.addView(name);b.addView(newPassword);b.addView(confirm);\n','        b.addView(name);b.addView(newPassword);b.addView(confirm);addPasswordVisibility(b,newPassword,confirm);\n')
replace_once(MAIN,'EditText existingEmail=input("Invited email",invitedEmail);existingEmail.setEnabled(invitedEmail.isEmpty());EditText existingPassword=input("Password","");existingPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(existingEmail);b.addView(existingPassword);','EditText existingEmail=input("Invited email",invitedEmail);existingEmail.setEnabled(invitedEmail.isEmpty());EditText existingPassword=input("Password","");existingPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(existingEmail);b.addView(existingPassword);addPasswordVisibility(b,existingPassword);')

replace_once(MAIN,'runCloud("Loading "+wm.name+"…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Welcome to "+wm.name+" · "+wm.role);showDashboard();});','runCloud("Loading "+wm.name+"…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{showWorkspaceReady(wm,(CloudSyncFoundation.SyncResult)sync);});')
replace_once(MAIN,'runCloud("Loading "+wm.name+"…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Joined "+wm.name+" as "+wm.role);showDashboard();});','runCloud("Loading "+wm.name+"…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{showWorkspaceReady(wm,(CloudSyncFoundation.SyncResult)sync);});')

replace_once(
    MAIN,
    '        setHeader("Account & Workspace","Identity, workspace access & cloud sync");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);\n        if(hasPendingWorkspaceInvite()&&!accountTeam.hasCloudWorkspace()){showPendingInviteOnboarding(b);return;}\n',
    '        setHeader("Account & Workspace","Your account is you · a workspace is your company");clear();LinearLayout b=body(page());MaterialButton back=outlineButton(firstRunFlow?"← Welcome":"← Back");back.setOnClickListener(v->{if(firstRunFlow)showFirstRunWelcome();else showMore();});b.addView(back);\n        if(hasPendingWorkspaceInvite()&&!accountTeam.hasCloudWorkspace()){showPendingInviteOnboarding(b);return;}\n        String accountState=cloudSync.signedIn()?cloudSync.accountEmail():"Not signed in";String workspaceState=accountTeam.hasCloudWorkspace()?"Cloud workspace · "+accountTeam.workspaceName():accountTeam.hasWorkspace()?"Local workspace · "+accountTeam.workspaceName():"No workspace selected";b.addView(heroCard(accountTeam.hasWorkspace()?accountTeam.workspaceName():"Account & workspace",accountState+"\\n"+workspaceState));b.addView(paragraph("Your Fida Field account identifies you. The workspace contains your company data, team permissions and shared service records."));\n'
)

replace_once(MAIN,'        if(canManageWorkspaceSettings()){b.addView(section("Local workspace"));','        if(canManageWorkspaceSettings()&&!(firstRunFlow&&!cloudSync.signedIn())){b.addView(section("Workspace profile"));')

replace_once(MAIN,'EditText cloudEmail=input("Email",val(localEmail));EditText password=input("Password","");password.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(cloudEmail);b.addView(password);','EditText cloudEmail=input("Email",val(localEmail));EditText password=input("Password","");password.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(cloudEmail);b.addView(password);addPasswordVisibility(b,password);')

old_signin='''            signIn.setOnClickListener(v->{String e=val(cloudEmail),p=val(password),n=val(person);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){cloudEmail.setError("Valid email required");return;}if(p.isEmpty()){password.setError("Password required");return;}runCloud("Signing in…",()->{SupabaseClientLite.AuthResult ar=cloudSync.signIn(e,p);CloudSyncFoundation.WorkspaceMembership wm=cloudSync.firstWorkspace();return new Object[]{ar,wm};},obj->{Object[] r=(Object[])obj;SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)r[0];CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)r[1];accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(wm!=null)accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast(wm==null?"Signed in · create or accept a workspace":"Signed in to "+wm.name);showAccountWorkspace();});});\n'''
new_signin='''            signIn.setOnClickListener(v->{String e=val(cloudEmail),p=val(password),n=val(person);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){cloudEmail.setError("Valid email required");return;}if(p.isEmpty()){password.setError("Password required");return;}runCloud("Signing in…",()->{SupabaseClientLite.AuthResult ar=cloudSync.signIn(e,p);CloudSyncFoundation.WorkspaceMembership wm=cloudSync.firstWorkspace();return new Object[]{ar,wm};},obj->{Object[] r=(Object[])obj;SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)r[0];CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)r[1];String display=n;if(display==null||display.trim().isEmpty()){int at=ar.email.indexOf('@');display=at>0?ar.email.substring(0,at):ar.email;}accountTeam.bindCloudAccount(ar.userId,display,ar.email);if(wm!=null){accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);if(firstRunFlow){runCloud("Loading "+wm.name+"…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{showWorkspaceReady(wm,(CloudSyncFoundation.SyncResult)sync);});}else{toast("Signed in to "+wm.name);showAccountWorkspace();}}else{toast("Signed in · no workspace membership found");showAccountWorkspace();}});});\n'''
replace_once(MAIN,old_signin,new_signin)

old_signup='''            signUp.setOnClickListener(v->{String e=val(cloudEmail),p=val(password),n=val(person);if(n.isEmpty()){person.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){cloudEmail.setError("Valid email required");return;}if(p.length()<8){password.setError("Use at least 8 characters");return;}runCloud("Creating account…",()->cloudSync.signUp(n,e,p),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(ar.signedIn){toast("Account created and signed in");showAccountWorkspace();}else new MaterialAlertDialogBuilder(this).setTitle("Confirm your email").setMessage("Supabase created the account. Open the confirmation email, confirm it, then return here and sign in with the same password.").setPositiveButton("OK",null).show();});});\n'''
replace_once(MAIN,old_signup,'            signUp.setOnClickListener(v->showCreateCloudAccountDialog(val(person),val(cloudEmail)));\n')

old_create='''            b.addView(section("Create or join workspace"));if(canManageWorkspaceSettings()){MaterialButton create=button("Create cloud workspace");create.setOnClickListener(v->{String name=val(workspace);if(name.isEmpty()){workspace.setError("Workspace name required");return;}runCloud("Creating cloud workspace…",()->cloudSync.createWorkspace(name),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Cloud workspace created");showAccountWorkspace();});});b.addView(create);}\n'''
new_create='''            b.addView(section("Create or join workspace"));if(canManageWorkspaceSettings()){MaterialButton create=button("Create cloud workspace");create.setOnClickListener(v->{String name=val(workspace);if(name.isEmpty()){workspace.setError("Workspace name required");return;}runCloud("Creating cloud workspace…",()->cloudSync.createWorkspace(name),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);runCloud("Preparing "+wm.name+"…",()->cloudSync.syncNow(wm.id,true),sync->{showWorkspaceReady(wm,(CloudSyncFoundation.SyncResult)sync);});});});b.addView(create);}\n'''
replace_once(MAIN,old_create,new_create)

old_reset='''        EditText password=field("New password");password.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);EditText confirm=field("Confirm new password");confirm.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);body.addView(password);body.addView(confirm);\n        TextView hint=text("Use at least 8 characters. Your workspace, jobs, history and permissions will stay unchanged.");hint.setTextSize(12);body.addView(hint);\n'''
new_reset='''        EditText password=field("New password");password.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);EditText confirm=field("Confirm new password");confirm.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);body.addView(password);body.addView(confirm);\n        com.google.android.material.materialswitch.MaterialSwitch show=new com.google.android.material.materialswitch.MaterialSwitch(this);show.setText("Show password");show.setOnCheckedChangeListener((button,checked)->{password.setTransformationMethod(checked?android.text.method.HideReturnsTransformationMethod.getInstance():android.text.method.PasswordTransformationMethod.getInstance());confirm.setTransformationMethod(checked?android.text.method.HideReturnsTransformationMethod.getInstance():android.text.method.PasswordTransformationMethod.getInstance());password.setSelection(password.length());confirm.setSelection(confirm.length());});body.addView(show);\n        TextView hint=text("Use at least 8 characters. Your workspace, jobs, history and permissions will stay unchanged.");hint.setTextSize(12);body.addView(hint);\n'''
replace_once(RESET,old_reset,new_reset)

print('Fida Field 0.9.47 first-run and account UX patch applied')
