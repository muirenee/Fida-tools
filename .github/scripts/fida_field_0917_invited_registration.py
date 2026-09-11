from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

# Public Edge Function invocation is used only for a one-time invitation-token registration endpoint.
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/SupabaseClientLite.java')
s=p.read_text()
anchor='''    public Object invokeFunction(String function,JSONObject body)throws Exception{\n        String name=function==null?"":function.trim();if(name.isEmpty())throw new Exception("Missing Edge Function name");\n        return request("POST",BuildConfig.SUPABASE_URL+"/functions/v1/"+enc(name),body==null?new JSONObject():body,true,null,null);\n    }'''
replacement=anchor+'''\n\n    public Object invokePublicFunction(String function,JSONObject body)throws Exception{\n        String name=function==null?"":function.trim();if(name.isEmpty())throw new Exception("Missing Edge Function name");\n        return request("POST",BuildConfig.SUPABASE_URL+"/functions/v1/"+enc(name),body==null?new JSONObject():body,false,null,null);\n    }'''
s=replace_once(s,anchor,replacement,'public edge function client')
p.write_text(s)

# Cloud helper creates a confirmed invited account, then signs it in.
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s=p.read_text()
anchor='''    public SupabaseClientLite.AuthResult signUp(String name,String email,String password)throws Exception{return client.signUp(name,email,password);}\n    public SupabaseClientLite.AuthResult signIn(String email,String password)throws Exception{return client.signIn(email,password);}\n    public void signOut()throws Exception{client.signOut();}'''
replacement='''    public SupabaseClientLite.AuthResult signUp(String name,String email,String password)throws Exception{return client.signUp(name,email,password);}\n    public SupabaseClientLite.AuthResult signIn(String email,String password)throws Exception{return client.signIn(email,password);}\n    public WorkspaceMembership registerInvitedUser(String token,String name,String password)throws Exception{\n        Object raw=client.invokePublicFunction("register-invited-user",new JSONObject().put("token",token==null?"":token.trim()).put("name",name==null?"":name.trim()).put("password",password));\n        if(!(raw instanceof JSONObject))throw new Exception("Invitation registration returned an unexpected response");\n        JSONObject o=(JSONObject)raw;if(!o.optBoolean("ok",false))throw new Exception(o.optString("message","Could not create invited account"));\n        String email=o.optString("email","");if(email.isEmpty())throw new Exception("Invitation email was not returned");\n        client.signIn(email,password);\n        return new WorkspaceMembership(o.optString("workspace_id",""),o.optString("workspace_name","Workspace"),AccountTeamManager.normalizeRole(o.optString("role","technician")));\n    }\n    public void signOut()throws Exception{client.signOut();}'''
s=replace_once(s,anchor,replacement,'invited registration cloud helper')
p.write_text(s)

# Replace invited-user onboarding create-account action with one server-verified registration/join step.
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s=p.read_text()
old='''        MaterialButton create=button("Create account & join");create.setOnClickListener(v->{String n=val(name),e=val(email),pw=val(password);if(n.isEmpty()){name.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(pw.length()<6){password.setError("Use at least 6 characters");return;}runCloud("Creating account…",()->cloudSync.signUp(n,e,pw),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(ar.signedIn)acceptPendingInviteNow(n);else new MaterialAlertDialogBuilder(this).setTitle("One confirmation step").setMessage("We created your account. Confirm the email from Fida Field/Supabase once, then return here and tap Sign in & join. The workspace invitation is already saved — you will not need to enter the code.").setPositiveButton("OK",(d,w)->showAccountWorkspace()).show();});});b.addView(create);'''
new='''        MaterialButton create=button("Create account & join");create.setOnClickListener(v->{String n=val(name),e=val(email),pw=val(password);if(n.isEmpty()){name.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(pw.length()<8){password.setError("Use at least 8 characters");return;}runCloud("Creating your account and joining workspace…",()->cloudSync.registerInvitedUser(token,n,pw),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudAccount(cloudSync.userId(),n,cloudSync.accountEmail());accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);clearPendingWorkspaceInvite();runCloud("Loading your workspace…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Welcome to "+wm.name+" · "+wm.role);showDashboard();});});});b.addView(create);'''
s=replace_once(s,old,new,'one-step invited account creation')
s=replace_once(s,
'''        b.addView(section("Workspace invitation"));b.addView(paragraph("Invitation loaded from your email. No code entry is required. Create an account or sign in with the invited email and Fida Field will join the workspace automatically."));''',
'''        b.addView(section("Workspace invitation"));b.addView(paragraph("Invitation loaded from your email. New users only enter their name and choose a password; Fida Field creates the account, verifies the invitation and joins the workspace in one step. Existing users can sign in and join."));''',
'invite onboarding explanation')
p.write_text(s)
