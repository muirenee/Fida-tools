from pathlib import Path

GRADLE=Path('fida-field/app/build.gradle')
CLOUD=Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
MAIN=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')


def replace_once(path:Path,old:str,new:str):
    text=path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:180]!r}')
    path.write_text(text.replace(old,new,1))


def replace_between(path:Path,start_marker:str,end_marker:str,new_block:str):
    text=path.read_text()
    start=text.find(start_marker)
    if start<0: raise SystemExit(f'Start marker not found in {path}: {start_marker}')
    end=text.find(end_marker,start)
    if end<0: raise SystemExit(f'End marker not found in {path}: {end_marker}')
    path.write_text(text[:start]+new_block+text[end:])

replace_once(GRADLE,"versionCode 47\n        versionName '0.9.44-test'","versionCode 48\n        versionName '0.9.45-test'")

replace_once(
    CLOUD,
    '    public void requestPasswordReset(String email)throws Exception{client.requestPasswordReset(email);}\n',
    '''    public void requestPasswordReset(String email)throws Exception{client.requestPasswordReset(email);}\n    public JSONObject previewWorkspaceInvite(String token)throws Exception{\n        String code=token==null?"":token.trim();if(code.isEmpty())throw new Exception("Invitation code is required");\n        Object raw=client.invokePublicFunction("workspace-invite-link",new JSONObject().put("token",code).put("format","json"));\n        if(!(raw instanceof JSONObject))throw new Exception("Invitation could not be checked");JSONObject o=(JSONObject)raw;\n        if(!o.optBoolean("ok",false))throw new Exception(o.optString("message","Invitation is not available"));return o;\n    }\n'''
)

old_keys='''    private static final String KEY_PENDING_INVITE_TOKEN="pending_workspace_invite_token";\n    private static final String KEY_PENDING_INVITE_EMAIL="pending_workspace_invite_email";\n    private boolean captureWorkspaceInviteIntent(Intent intent){\n        Uri data=intent==null?null:intent.getData();if(data==null||!"fidafield".equalsIgnoreCase(data.getScheme())||!"workspace-invite".equalsIgnoreCase(data.getHost()))return false;\n        String token=data.getQueryParameter("token"),email=data.getQueryParameter("email");if(token==null||token.trim().isEmpty())return false;\n        prefs.edit().putString(KEY_PENDING_INVITE_TOKEN,token.trim()).putString(KEY_PENDING_INVITE_EMAIL,email==null?"":email.trim()).apply();return true;\n    }\n    private boolean hasPendingWorkspaceInvite(){return !prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim().isEmpty();}\n    private String pendingWorkspaceInviteToken(){return prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim();}\n    private String pendingWorkspaceInviteEmail(){return prefs.getString(KEY_PENDING_INVITE_EMAIL,"").trim();}\n    private void clearPendingWorkspaceInvite(){prefs.edit().remove(KEY_PENDING_INVITE_TOKEN).remove(KEY_PENDING_INVITE_EMAIL).apply();}\n'''
new_keys='''    private static final String KEY_PENDING_INVITE_TOKEN="pending_workspace_invite_token";\n    private static final String KEY_PENDING_INVITE_EMAIL="pending_workspace_invite_email";\n    private static final String KEY_PENDING_INVITE_WORKSPACE="pending_workspace_invite_workspace";\n    private static final String KEY_PENDING_INVITE_ROLE="pending_workspace_invite_role";\n    private static final String KEY_PENDING_INVITE_EXPIRES="pending_workspace_invite_expires";\n    private boolean captureWorkspaceInviteIntent(Intent intent){\n        Uri data=intent==null?null:intent.getData();if(data==null||!"fidafield".equalsIgnoreCase(data.getScheme())||!"workspace-invite".equalsIgnoreCase(data.getHost()))return false;\n        String token=data.getQueryParameter("token"),email=data.getQueryParameter("email");if(token==null||token.trim().isEmpty())return false;\n        prefs.edit().putString(KEY_PENDING_INVITE_TOKEN,token.trim()).putString(KEY_PENDING_INVITE_EMAIL,email==null?"":email.trim()).putString(KEY_PENDING_INVITE_WORKSPACE,safeQuery(data,"workspace")).putString(KEY_PENDING_INVITE_ROLE,safeQuery(data,"role")).putString(KEY_PENDING_INVITE_EXPIRES,safeQuery(data,"expires")).apply();return true;\n    }\n    private String safeQuery(Uri data,String key){String v=data==null?null:data.getQueryParameter(key);return v==null?"":v.trim();}\n    private boolean hasPendingWorkspaceInvite(){return !prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim().isEmpty();}\n    private String pendingWorkspaceInviteToken(){return prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim();}\n    private String pendingWorkspaceInviteEmail(){return prefs.getString(KEY_PENDING_INVITE_EMAIL,"").trim();}\n    private String pendingWorkspaceInviteWorkspace(){return prefs.getString(KEY_PENDING_INVITE_WORKSPACE,"").trim();}\n    private String pendingWorkspaceInviteRole(){return prefs.getString(KEY_PENDING_INVITE_ROLE,"").trim();}\n    private String pendingWorkspaceInviteExpires(){return prefs.getString(KEY_PENDING_INVITE_EXPIRES,"").trim();}\n    private void cacheWorkspaceInvite(JSONObject o){if(o==null)return;prefs.edit().putString(KEY_PENDING_INVITE_TOKEN,o.optString("token",pendingWorkspaceInviteToken())).putString(KEY_PENDING_INVITE_EMAIL,o.optString("email",pendingWorkspaceInviteEmail())).putString(KEY_PENDING_INVITE_WORKSPACE,o.optString("workspace_name",pendingWorkspaceInviteWorkspace())).putString(KEY_PENDING_INVITE_ROLE,o.optString("role",pendingWorkspaceInviteRole())).putString(KEY_PENDING_INVITE_EXPIRES,o.optString("expires_at",pendingWorkspaceInviteExpires())).apply();}\n    private void clearPendingWorkspaceInvite(){prefs.edit().remove(KEY_PENDING_INVITE_TOKEN).remove(KEY_PENDING_INVITE_EMAIL).remove(KEY_PENDING_INVITE_WORKSPACE).remove(KEY_PENDING_INVITE_ROLE).remove(KEY_PENDING_INVITE_EXPIRES).apply();}\n'''
replace_once(MAIN,old_keys,new_keys)

new_invite_block=r'''    private void showPendingInviteOnboarding(LinearLayout b){
        String token=pendingWorkspaceInviteToken(),invitedEmail=pendingWorkspaceInviteEmail(),workspaceName=pendingWorkspaceInviteWorkspace(),inviteRole=pendingWorkspaceInviteRole(),expires=pendingWorkspaceInviteExpires();
        String target=workspaceName.isEmpty()?"your workspace":workspaceName;String role=inviteRole.isEmpty()?"workspace member":inviteRole;
        b.addView(heroCard(workspaceName.isEmpty()?"Workspace invitation":"Join "+workspaceName,"You were invited as "+role+". Fida Field will keep your existing workspace history and permissions tied to this account."));
        if(!invitedEmail.isEmpty())b.addView(info("Invited account",invitedEmail));if(!inviteRole.isEmpty())b.addView(info("Access role",inviteRole));if(!expires.isEmpty())b.addView(info("Invitation expires",expires));
        b.addView(paragraph("Joining is completed in three steps: confirm your account, accept the invitation, then Fida Field loads the workspace automatically."));
        if(!cloudSync.backendConfigured()){b.addView(empty("This build does not contain the Supabase cloud configuration."));return;}
        if(cloudSync.signedIn()){
            String signed=cloudSync.accountEmail();b.addView(section("Your account"));b.addView(info("Signed in as",signed));
            if(!invitedEmail.isEmpty()&&!signed.equalsIgnoreCase(invitedEmail)){
                b.addView(empty("This invitation belongs to "+invitedEmail+", but this device is signed in as "+signed+"."));
                MaterialButton out=button("Sign out & continue with invited account");out.setOnClickListener(v->runCloud("Signing out…",()->{cloudSync.signOut();return null;},obj->{accountTeam.clearCloudBinding();showAccountWorkspace();}));b.addView(out);
                MaterialButton close=outlineButton("Close this invitation");close.setOnClickListener(v->{clearPendingWorkspaceInvite();showAccountWorkspace();});b.addView(close);return;
            }
            b.addView(paragraph("You already have the correct Fida Field account. No new account will be created."));
            MaterialButton join=button(workspaceName.isEmpty()?"Join workspace now":"Join "+workspaceName);join.setOnClickListener(v->acceptPendingInviteNow(accountTeam.accountName()));b.addView(join);
            MaterialButton close=outlineButton("Close this invitation");close.setOnClickListener(v->{clearPendingWorkspaceInvite();showAccountWorkspace();});b.addView(close);return;
        }

        b.addView(section("New to Fida Field?"));
        b.addView(paragraph("Create your account and join "+target+" in one step."));
        EditText name=input("Your name",accountTeam.accountName().isEmpty()?prefs.getString("technician_name",""):accountTeam.accountName());
        EditText newPassword=input("Create password","");newPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText confirm=input("Confirm password","");confirm.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        b.addView(name);b.addView(newPassword);b.addView(confirm);
        MaterialButton create=button("Create account & join");create.setOnClickListener(v->{String n=val(name),pw=val(newPassword),cpw=val(confirm);if(n.isEmpty()){name.setError("Your name required");return;}if(invitedEmail.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(invitedEmail).matches()){toast("Invitation email is missing. Reopen the email link or use the invitation code.");return;}if(pw.length()<8){newPassword.setError("Use at least 8 characters");return;}if(!pw.equals(cpw)){confirm.setError("Passwords do not match");return;}runCloud("Creating your account & joining…",()->cloudSync.registerInvitedUser(token,n,pw),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudAccount(cloudSync.userId(),n,cloudSync.accountEmail());accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);clearPendingWorkspaceInvite();runCloud("Loading "+wm.name+"…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Welcome to "+wm.name+" · "+wm.role);showDashboard();});});});b.addView(create);

        b.addView(section("Already have a Fida Field account?"));
        b.addView(paragraph("Sign in with the invited email. Your account will be added to "+target+" without creating another account."));
        EditText existingEmail=input("Invited email",invitedEmail);existingEmail.setEnabled(invitedEmail.isEmpty());EditText existingPassword=input("Password","");existingPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(existingEmail);b.addView(existingPassword);
        MaterialButton signIn=button("Sign in & join");signIn.setOnClickListener(v->{String e=val(existingEmail),pw=val(existingPassword);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){existingEmail.setError("Valid email required");return;}if(!invitedEmail.isEmpty()&&!e.equalsIgnoreCase(invitedEmail)){existingEmail.setError("Use the invited email address");return;}if(pw.isEmpty()){existingPassword.setError("Password required");return;}runCloud("Signing in…",()->cloudSync.signIn(e,pw),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;String n=accountTeam.accountName();if(n==null||n.trim().isEmpty())n=prefs.getString("technician_name","");if(n==null||n.trim().isEmpty()){int at=ar.email.indexOf('@');n=at>0?ar.email.substring(0,at):ar.email;}accountTeam.bindCloudAccount(ar.userId,n,ar.email);acceptPendingInviteNow(n);});});b.addView(signIn);
        MaterialButton forgotInvite=outlineButton("Forgot password?");forgotInvite.setOnClickListener(v->showForgotPassword(val(existingEmail)));b.addView(forgotInvite);
        MaterialButton other=outlineButton("Use another invitation code");other.setOnClickListener(v->{clearPendingWorkspaceInvite();showJoinCodeDialog();});b.addView(other);
        b.addView(paragraph("Your workspace data stays protected by the role selected by the Owner or Admin who invited you."));
    }

    private void showJoinCodeDialog(){
        if(!cloudSync.backendConfigured()){toast("Cloud service is not configured in this build");return;}
        LinearLayout f=form();f.addView(paragraph("Paste the invitation code from your Fida Field email. We will verify it before asking you to sign in or create an account."));EditText code=input("Invitation code","");f.addView(code);
        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Join a workspace").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Continue",null).create();d.setCanceledOnTouchOutside(false);
        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String c=val(code);if(c.isEmpty()){code.setError("Invitation code required");return;}runCloud("Checking invitation…",()->cloudSync.previewWorkspaceInvite(c),obj->{d.dismiss();cacheWorkspaceInvite((JSONObject)obj);showAccountWorkspace();});}));d.show();
    }

'''
replace_between(MAIN,'    private void showPendingInviteOnboarding(LinearLayout b){','    private void showForgotPassword(String suggestedEmail){',new_invite_block)

replace_between(
    MAIN,
    '    private void acceptPendingInviteNow(String displayName){',
    '    private void showAccountWorkspace(){',
    r'''    private void acceptPendingInviteNow(String displayName){
        String token=pendingWorkspaceInviteToken();if(token.isEmpty()){showAccountWorkspace();return;}String n=displayName==null?"":displayName.trim();if(n.isEmpty())n=prefs.getString("technician_name","");if(n.isEmpty()){String e=cloudSync.accountEmail();int at=e.indexOf('@');n=at>0?e.substring(0,at):e;}final String finalName=n;
        runCloud("Joining workspace…",()->cloudSync.acceptInvite(token),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudAccount(cloudSync.userId(),finalName,cloudSync.accountEmail());accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);clearPendingWorkspaceInvite();runCloud("Loading "+wm.name+"…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Joined "+wm.name+" as "+wm.role);showDashboard();});});
    }

'''
)

replace_once(
    MAIN,
    '        if(!cloudSync.signedIn()){\n            EditText cloudEmail=input("Email",val(localEmail));',
    '        if(!cloudSync.signedIn()){\n            MaterialButton joinInvite=outlineButton("Join with invitation code");joinInvite.setOnClickListener(v->showJoinCodeDialog());b.addView(joinInvite);b.addView(paragraph("If your company invited you, use the invitation link in the email or paste the invitation code here. You do not need to create a separate workspace."));\n            EditText cloudEmail=input("Email",val(localEmail));'
)

replace_once(MAIN,'if(p.length()<6){password.setError("Use at least 6 characters");return;}','if(p.length()<8){password.setError("Use at least 8 characters");return;}')

old_join='''            EditText invite=input("Invitation code","");b.addView(invite);MaterialButton accept=outlineButton("Accept invitation");accept.setOnClickListener(v->{String code=val(invite);if(code.isEmpty()){invite.setError("Invitation code required");return;}runCloud("Accepting invitation…",()->cloudSync.acceptInvite(code),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Joined "+wm.name);showAccountWorkspace();});});b.addView(accept);'''
new_join='''            MaterialButton joinCode=outlineButton("Join with invitation code");joinCode.setOnClickListener(v->showJoinCodeDialog());b.addView(joinCode);'''
replace_once(MAIN,old_join,new_join)

replace_once(MAIN,'setTitle("Invite workspace member")','setTitle("Invite to "+accountTeam.workspaceName())')
replace_once(MAIN,'setPositiveButton("Create invitation",null)','setPositiveButton(accountTeam.hasCloudWorkspace()?"Send invitation":"Create invitation",null)')

print('Fida Field 0.9.45 workspace join UX patch applied')
