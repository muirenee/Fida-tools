from pathlib import Path

# BuildConfig/version: keep the publishable key out of source and inject it from GitHub Actions.
gradle = Path('fida-field/app/build.gradle')
g = gradle.read_text()
assert "versionCode 11" in g and "versionName '0.9.8.1-test'" in g
g = g.replace('versionCode 11', 'versionCode 12', 1).replace("versionName '0.9.8.1-test'", "versionName '0.9.9-test'", 1)
marker = "    signingConfigs {"
assert marker in g
config = """    buildFeatures {\n        buildConfig true\n    }\n\n"""
default_end = "        versionName '0.9.9-test'\n    }\n\n"
assert default_end in g
default_new = """        versionName '0.9.9-test'\n        buildConfigField 'String', 'SUPABASE_URL', '\"https://owxoyxylileuagsnjjht.supabase.co\"'\n        buildConfigField 'String', 'SUPABASE_PUBLISHABLE_KEY', '\"' + (System.getenv('SUPABASE_PUBLISHABLE_KEY') ?: '') + '\"'\n    }\n\n"""
g = g.replace(default_end, default_new, 1)
g = g.replace(marker, config + marker, 1)
gradle.write_text(g)

# Database v5: cloud identifiers, invite codes, core push/pull helpers.
dbfile = Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
s = dbfile.read_text()
assert 'DB_VERSION = 4' in s
s = s.replace('DB_VERSION = 4', 'DB_VERSION = 5', 1)
s = s.replace('member_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL', 'member_uuid TEXT NOT NULL UNIQUE, user_uuid TEXT, name TEXT NOT NULL', 1)
s = s.replace("status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)", "status TEXT NOT NULL DEFAULT 'Pending', token TEXT, expires_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)", 1)
upgrade_anchor = '            db.execSQL("CREATE INDEX IF NOT EXISTS idx_workspace_invites_workspace ON workspace_invites(workspace_id,status)");\n        }\n    }\n\n    public String today()'
assert upgrade_anchor in s
upgrade = '''            db.execSQL("CREATE INDEX IF NOT EXISTS idx_workspace_invites_workspace ON workspace_invites(workspace_id,status)");
        }
        if(oldVersion<5){
            db.execSQL("ALTER TABLE workspace_members ADD COLUMN user_uuid TEXT");
            db.execSQL("ALTER TABLE workspace_invites ADD COLUMN token TEXT");
            db.execSQL("ALTER TABLE workspace_invites ADD COLUMN expires_at TEXT");
        }
    }

    public String today()'''
s = s.replace(upgrade_anchor, upgrade, 1)
method_anchor = '    public List<Row> pendingSyncRows(){return rows("SELECT q.*,m.remote_uuid,m.server_version,m.last_synced_at FROM sync_queue q LEFT JOIN sync_metadata m ON m.entity_type=q.entity_type AND m.entity_id=q.entity_id ORDER BY q.changed_at,q.id",null);}\n\n'
assert method_anchor in s
methods = r'''    public long pendingBusinessChanges(){return count("sync_queue","entity_type IN ('customer','site','asset','technician','job')",null);}
    public List<Row> pendingBusinessSyncRows(){return rows("SELECT q.*,m.remote_uuid,m.server_version,m.last_synced_at FROM sync_queue q LEFT JOIN sync_metadata m ON m.entity_type=q.entity_type AND m.entity_id=q.entity_id WHERE q.entity_type IN ('customer','site','asset','technician','job') ORDER BY q.changed_at,q.id",null);}
    public Row syncEntity(String type,long id){if("customer".equals(type))return getCustomer(id);if("site".equals(type))return getSite(id);if("asset".equals(type))return getAsset(id);if("technician".equals(type))return getTechnician(id);if("job".equals(type))return one("SELECT * FROM jobs WHERE id=?",new String[]{String.valueOf(id)});return new Row();}
    public long localIdForRemote(String type,String remoteUuid){if(remoteUuid==null||remoteUuid.isEmpty())return 0;Row r=one("SELECT entity_id FROM sync_metadata WHERE entity_type=? AND remote_uuid=?",new String[]{type,remoteUuid});try{return Long.parseLong(r.s("entity_id"));}catch(Exception e){return 0;}}
    public void bindRemoteUuid(String type,long localId,String remoteUuid){if(localId<=0||remoteUuid==null||remoteUuid.isEmpty())return;Row old=one("SELECT id FROM sync_metadata WHERE entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)});ContentValues v=new ContentValues();v.put("remote_uuid",remoteUuid);v.put("last_synced_at",now());if(old.id()>0)getWritableDatabase().update("sync_metadata",v,"id=?",new String[]{String.valueOf(old.id())});else{v.put("entity_type",type);v.put("entity_id",localId);getWritableDatabase().insertOrThrow("sync_metadata",null,v);}}
    public void markEntitySynced(String type,long localId,String remoteUuid){bindRemoteUuid(type,localId,remoteUuid);getWritableDatabase().delete("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)});}
    public void rebindWorkspace(String oldId,String newId){if(oldId==null||newId==null||oldId.isEmpty()||newId.isEmpty()||oldId.equals(newId))return;ContentValues v=new ContentValues();v.put("workspace_id",newId);getWritableDatabase().update("workspace_members",v,"workspace_id=?",new String[]{oldId});getWritableDatabase().update("workspace_invites",v,"workspace_id=?",new String[]{oldId});}
    public void cacheWorkspaceTeam(String workspaceId,JSONArray members,JSONArray invites)throws Exception{
        SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{d.delete("workspace_members","workspace_id=?",new String[]{workspaceId});d.delete("workspace_invites","workspace_id=?",new String[]{workspaceId});
            for(int i=0;i<members.length();i++){JSONObject o=members.getJSONObject(i);ContentValues v=new ContentValues();v.put("workspace_id",workspaceId);v.put("member_uuid",o.optString("member_id",java.util.UUID.randomUUID().toString()));v.put("user_uuid",o.optString("user_id",""));String name=o.optString("full_name","");String email=o.optString("email","");v.put("name",name.isEmpty()?(email.isEmpty()?"Team member":email):name);v.put("email",email);v.put("role",AccountTeamManager.normalizeRole(o.optString("role","technician")));v.put("status",AccountTeamManager.normalizeStatus(o.optString("status","active")));v.put("created_at",now());v.put("updated_at",now());d.insertOrThrow("workspace_members",null,v);}
            for(int i=0;i<invites.length();i++){JSONObject o=invites.getJSONObject(i);ContentValues v=new ContentValues();v.put("workspace_id",workspaceId);v.put("invite_uuid",o.optString("invite_id",java.util.UUID.randomUUID().toString()));v.put("email",o.optString("email",""));v.put("role",AccountTeamManager.normalizeRole(o.optString("role","technician")));v.put("status",AccountTeamManager.normalizeStatus(o.optString("status","pending")));v.put("token",o.optString("token",""));v.put("expires_at",o.optString("expires_at",""));v.put("created_at",now());v.put("updated_at",now());d.insertOrThrow("workspace_invites",null,v);}
            d.delete("sync_queue","entity_type IN ('workspace_member','workspace_invite')",null);d.setTransactionSuccessful();}finally{d.endTransaction();}
    }
    private String j(JSONObject o,String k){return o==null||o.isNull(k)?"":o.optString(k,"");}
    private void jt(ContentValues v,JSONObject o,String... keys){for(String k:keys)v.put(k,j(o,k));}
    private long remoteLocal(String type,JSONObject o,String key){String u=j(o,key);return u.isEmpty()?0:localIdForRemote(type,u);}
    public long upsertRemoteEntity(String type,JSONObject o)throws Exception{
        String remote=j(o,"id");if(remote.isEmpty())return 0;long local=localIdForRemote(type,remote);SQLiteDatabase d=getWritableDatabase();ContentValues v=new ContentValues();
        if("customer".equals(type)){jt(v,o,"name","contact","phone","email","address","notes");if(local==0){v.put("created_at",now());local=d.insertOrThrow("customers",null,v);}else d.update("customers",v,"id=?",new String[]{String.valueOf(local)});}
        else if("site".equals(type)){long cid=remoteLocal("customer",o,"customer_id");if(cid<=0)return 0;jt(v,o,"name","address","contact","phone","notes");v.put("customer_id",cid);if(local==0){v.put("created_at",now());local=d.insertOrThrow("sites",null,v);}else d.update("sites",v,"id=?",new String[]{String.valueOf(local)});}
        else if("asset".equals(type)){if(local==0&&!j(o,"tag").isEmpty())local=getAssetByTag(j(o,"tag")).id();jt(v,o,"tag","name","category","make_model","serial","location","notes","next_service");long cid=remoteLocal("customer",o,"customer_id"),sid=remoteLocal("site",o,"site_id");if(cid>0)v.put("customer_id",cid);else v.putNull("customer_id");if(sid>0)v.put("site_id",sid);else v.putNull("site_id");v.put("interval_days",o.optInt("interval_days",0));if(local==0){v.put("created_at",now());local=d.insertOrThrow("assets",null,v);}else d.update("assets",v,"id=?",new String[]{String.valueOf(local)});}
        else if("technician".equals(type)){jt(v,o,"name","role","phone","email");v.put("active",o.optBoolean("active",true)?1:0);if(local==0){v.put("created_at",now());local=d.insertOrThrow("technicians",null,v);}else d.update("technicians",v,"id=?",new String[]{String.valueOf(local)});}
        else if("job".equals(type)){if(local==0&&!j(o,"report_no").isEmpty())local=one("SELECT * FROM jobs WHERE report_no=?",new String[]{j(o,"report_no")}).id();jt(v,o,"report_no","title","problem","diagnosis","work_done","parts","priority","status","job_date","next_service","customer_name_signed");v.put("technician",j(o,"technician_name"));long cid=remoteLocal("customer",o,"customer_id"),sid=remoteLocal("site",o,"site_id"),aid=remoteLocal("asset",o,"asset_id");if(cid>0)v.put("customer_id",cid);else v.putNull("customer_id");if(sid>0)v.put("site_id",sid);else v.putNull("site_id");if(aid>0)v.put("asset_id",aid);else v.putNull("asset_id");v.put("updated_at",now());if(local==0){v.put("created_at",now());local=d.insertOrThrow("jobs",null,v);}else d.update("jobs",v,"id=?",new String[]{String.valueOf(local)});}
        else return 0;bindRemoteUuid(type,local,remote);d.delete("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(local)});return local;
    }

'''
s = s.replace(method_anchor, method_anchor + methods, 1)
dbfile.write_text(s)

# Main activity cloud account/team/sync UI.
main = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = main.read_text()
start = s.index('    private void showAccountWorkspace(){')
end = s.index('    private void showTeam(){', start)
account_block = r'''    private interface CloudWork { Object run() throws Exception; }
    private void runCloud(String started,CloudWork work,java.util.function.Consumer<Object> success){
        toast(started);new Thread(()->{try{Object result=work.run();runOnUiThread(()->success.accept(result));}catch(Exception e){String msg=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();cloudSync.markSyncResult(false,db.now(),msg);runOnUiThread(()->new MaterialAlertDialogBuilder(this).setTitle("Cloud operation failed").setMessage(msg).setPositiveButton("OK",null).show());}}).start();
    }

    private void showAccountWorkspace(){
        setHeader("Account & Workspace","Supabase identity, ownership & offline workspace");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        b.addView(section("Local workspace"));EditText workspace=input("Workspace / company name",accountTeam.workspaceName().isEmpty()?prefs.getString("company_name","Fidalix Limited"):accountTeam.workspaceName());EditText person=input("Your name",accountTeam.accountName().isEmpty()?prefs.getString("technician_name",""):accountTeam.accountName());EditText localEmail=input("Account email",accountTeam.accountEmail().isEmpty()?prefs.getString("company_email",""):accountTeam.accountEmail());b.addView(workspace);b.addView(person);b.addView(localEmail);
        MaterialButton save=outlineButton(accountTeam.hasWorkspace()?"Save local profile":"Create local workspace");save.setOnClickListener(v->{if(val(workspace).isEmpty()){workspace.setError("Workspace name required");return;}if(val(person).isEmpty()){person.setError("Your name required");return;}if(!val(localEmail).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(localEmail)).matches()){localEmail.setError("Enter a valid email");return;}accountTeam.saveOwnerWorkspace(val(workspace),val(person),val(localEmail));toast("Local workspace profile saved");showAccountWorkspace();});b.addView(save);
        b.addView(section("Cloud account"));b.addView(info("Provider",cloudSync.providerName()));b.addView(info("Backend",cloudSync.backendStatus()));
        if(!cloudSync.backendConfigured()){b.addView(empty("This build does not contain the Supabase publishable configuration."));return;}
        if(!cloudSync.signedIn()){
            EditText cloudEmail=input("Email",val(localEmail));EditText password=input("Password","");password.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(cloudEmail);b.addView(password);
            LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton signIn=button("Sign in");MaterialButton signUp=outlineButton("Create account");actions.addView(signIn,new LinearLayout.LayoutParams(0,dp(52),1));actions.addView(spacerH());actions.addView(signUp,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(actions);
            signIn.setOnClickListener(v->{String e=val(cloudEmail),p=val(password),n=val(person);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){cloudEmail.setError("Valid email required");return;}if(p.isEmpty()){password.setError("Password required");return;}runCloud("Signing in…",()->{SupabaseClientLite.AuthResult ar=cloudSync.signIn(e,p);CloudSyncFoundation.WorkspaceMembership wm=cloudSync.firstWorkspace();return new Object[]{ar,wm};},obj->{Object[] r=(Object[])obj;SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)r[0];CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)r[1];accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(wm!=null)accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast(wm==null?"Signed in · create or accept a workspace":"Signed in to "+wm.name);showAccountWorkspace();});});
            signUp.setOnClickListener(v->{String e=val(cloudEmail),p=val(password),n=val(person);if(n.isEmpty()){person.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){cloudEmail.setError("Valid email required");return;}if(p.length()<6){password.setError("Use at least 6 characters");return;}runCloud("Creating account…",()->cloudSync.signUp(n,e,p),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(ar.signedIn){toast("Account created and signed in");showAccountWorkspace();}else new MaterialAlertDialogBuilder(this).setTitle("Confirm your email").setMessage("Supabase created the account. Open the confirmation email, confirm it, then return here and sign in with the same password.").setPositiveButton("OK",null).show();});});
            b.addView(paragraph("Fida Field remains fully usable offline without signing in. Cloud sign-in is required only for multi-device synchronization and team workspaces."));return;
        }
        b.addView(info("Signed-in account",cloudSync.accountEmail()));b.addView(info("User ID",cloudSync.userId()));
        MaterialButton refresh=outlineButton("Refresh workspace membership");refresh.setOnClickListener(v->runCloud("Checking memberships…",()->cloudSync.firstWorkspace(),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;if(wm==null)toast("No cloud workspace membership found");else{accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Workspace refreshed");}showAccountWorkspace();}));b.addView(refresh);
        if(accountTeam.hasCloudWorkspace()){
            b.addView(section("Cloud workspace"));b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Workspace ID",accountTeam.workspaceId()));b.addView(info("Role",accountTeam.accountRole()));MaterialButton sync=button("Sync this workspace");sync.setOnClickListener(v->showCloudSync());b.addView(sync);
        }else{
            b.addView(section("Create or join workspace"));MaterialButton create=button("Create cloud workspace");create.setOnClickListener(v->{String name=val(workspace);if(name.isEmpty()){workspace.setError("Workspace name required");return;}runCloud("Creating cloud workspace…",()->cloudSync.createWorkspace(name),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Cloud workspace created");showAccountWorkspace();});});b.addView(create);
            EditText invite=input("Invitation code","");b.addView(invite);MaterialButton accept=outlineButton("Accept invitation");accept.setOnClickListener(v->{String code=val(invite);if(code.isEmpty()){invite.setError("Invitation code required");return;}runCloud("Accepting invitation…",()->cloudSync.acceptInvite(code),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Joined "+wm.name);showAccountWorkspace();});});b.addView(accept);
        }
        MaterialButton signOut=outlineButton("Sign out of cloud");signOut.setOnClickListener(v->runCloud("Signing out…",()->{cloudSync.signOut();return null;},obj->{accountTeam.clearCloudBinding();toast("Cloud account signed out · local data remains available");showAccountWorkspace();}));b.addView(signOut);
    }

'''
s = s[:start] + account_block + s[end:]

start = s.index('    private void showTeam(){')
end = s.index('    private void showInviteDialog(){', start)
team_block = r'''    private void showTeam(){
        setHeader("Team","Workspace members & invitations");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        if(!accountTeam.hasWorkspace()){b.addView(empty("Create your workspace before adding team members."));MaterialButton setup=button("Set up workspace");setup.setOnClickListener(v->showAccountWorkspace());b.addView(setup);return;}
        boolean cloud=accountTeam.hasCloudWorkspace()&&cloudSync.signedIn();b.addView(section(accountTeam.workspaceName()));b.addView(info("Your role",accountTeam.accountRole()));b.addView(info("Mode",cloud?"Cloud workspace · Supabase":"Local workspace"));
        if(cloud){MaterialButton refresh=outlineButton("Refresh team from cloud");refresh.setOnClickListener(v->runCloud("Refreshing team…",()->{cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{toast("Team refreshed");showTeam();}));b.addView(refresh);}
        if(accountTeam.canManageTeam()){MaterialButton invite=button("+ Invite member");invite.setOnClickListener(v->showInviteDialog());b.addView(invite);}else b.addView(paragraph("Only workspace Owners and Admins can manage members and invitations."));
        List<AppDatabase.Row> members=db.workspaceMembers(accountTeam.workspaceId());b.addView(section("Members ("+members.size()+")"));if(members.isEmpty())b.addView(empty(cloud?"Refresh the team to download workspace members.":"No members yet."));for(AppDatabase.Row r:members){String meta=(r.s("email").isEmpty()?"No email":r.s("email"))+" • "+r.s("status");MaterialCardView c=rowCard(r.s("name"),meta,r.s("role"));if(accountTeam.canManageTeam()&&!"Owner".equals(r.s("role")))c.setOnClickListener(v->showMemberDialog(r.id()));b.addView(c);}
        List<AppDatabase.Row> invites=db.workspaceInvites(accountTeam.workspaceId());b.addView(section("Invitations"));if(invites.isEmpty())b.addView(empty("No pending invitations."));for(AppDatabase.Row r:invites){MaterialCardView c=rowCard(r.s("email"),r.s("role"),r.s("status"));if("Pending".equals(r.s("status")))c.setOnClickListener(v->{String code=r.s("token");MaterialAlertDialogBuilder d=new MaterialAlertDialogBuilder(this).setTitle("Pending invitation").setMessage(r.s("email")+" · "+r.s("role")+(code.isEmpty()?"":"\n\nInvitation code:\n"+code)+(r.s("expires_at").isEmpty()?"":"\nExpires: "+r.s("expires_at"))).setNegativeButton("Close",null);if(!code.isEmpty())d.setNeutralButton("Copy code",(x,w)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",code));toast("Invitation code copied");});if(accountTeam.canManageTeam())d.setPositiveButton("Cancel invitation",(x,w)->{if(cloud)runCloud("Cancelling invitation…",()->{cloudSync.cancelInvite(r.s("invite_uuid"));cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return null;},z->{toast("Invitation cancelled");showTeam();});else{db.cancelWorkspaceInvite(r.id());showTeam();}});d.show();});b.addView(c);}
    }

'''
s = s[:start] + team_block + s[end:]

start = s.index('    private void showInviteDialog(){')
end = s.index('    private void showMemberDialog(long id){', start)
invite_block = r'''    private void showInviteDialog(){
        if(!accountTeam.canManageTeam()){toast("Owner or Admin access required");return;}LinearLayout f=form();EditText email=input("Email address","");Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});f.addView(email);f.addView(label("Role"));f.addView(role);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Invite team member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Create invitation",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String e=val(email),r=String.valueOf(role.getSelectedItem());if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){runCloud("Creating invitation…",()->{String token=cloudSync.createInvite(accountTeam.workspaceId(),e,r);cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return token;},obj->{d.dismiss();String token=String.valueOf(obj);new MaterialAlertDialogBuilder(this).setTitle("Invitation created").setMessage("Share this code with "+e+". They can sign in or create an account, then choose Accept invitation in Account & Workspace.\n\n"+token).setNegativeButton("Close",(a,b)->showTeam()).setPositiveButton("Copy code",(a,b)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",token));toast("Invitation code copied");showTeam();}).show();});}else{db.saveWorkspaceInvite(accountTeam.workspaceId(),e,r);d.dismiss();toast("Invitation saved locally");showTeam();}}));d.show();
    }

'''
s = s[:start] + invite_block + s[end:]

start = s.index('    private void showMemberDialog(long id){')
end = s.index('    private void showCloudSync(){', start)
member_block = r'''    private void showMemberDialog(long id){
        AppDatabase.Row r=db.getWorkspaceMember(id);if(r.id()==0)return;if("Owner".equals(r.s("role"))){toast("The workspace owner cannot be changed here");return;}LinearLayout f=form();EditText name=input("Name",r.s("name"));EditText email=input("Email",r.s("email"));name.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));email.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});setSpinner(role,r.s("role"));Spinner status=spinner(new String[]{"Active","Inactive"});setSpinner(status,r.s("status"));f.addView(name);f.addView(email);f.addView(label("Role"));f.addView(role);f.addView(label("Status"));f.addView(status);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Edit member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String rr=String.valueOf(role.getSelectedItem()),ss=String.valueOf(status.getSelectedItem());if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){runCloud("Updating member…",()->{cloudSync.updateMember(accountTeam.workspaceId(),r.s("member_uuid"),rr,ss);cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{d.dismiss();toast("Member updated");showTeam();});}else{if(val(name).isEmpty()){name.setError("Name required");return;}db.saveWorkspaceMember(id,accountTeam.workspaceId(),val(name),val(email),rr,ss);d.dismiss();toast("Member updated");showTeam();}}));d.show();
    }

'''
s = s[:start] + member_block + s[end:]

start = s.index('    private void showCloudSync(){')
end = s.index('    private void showUpgradeRequired(', start)
cloud_block = r'''    private void showCloudSync(){
        setHeader("Cloud & Team Sync","Live Supabase synchronization");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        b.addView(section("Workspace"));b.addView(info("Workspace",accountTeam.hasWorkspace()?accountTeam.workspaceName():"Not set up"));b.addView(info("Role",accountTeam.accountRole().isEmpty()?"Local user":accountTeam.accountRole()));b.addView(info("Cloud binding",accountTeam.hasCloudWorkspace()?"Bound":"Local only"));
        b.addView(section("Supabase"));b.addView(info("Status",cloudSync.backendStatus()));b.addView(info("Account",cloudSync.accountEmail().isEmpty()?"Not signed in":cloudSync.accountEmail()));b.addView(info("Last sync",cloudSync.lastSync()));b.addView(info("Last result",cloudSync.lastResult()));
        b.addView(section("This device"));b.addView(info("Device ID",cloudSync.deviceId()));b.addView(info("Pending business changes",String.valueOf(cloudSync.pendingChanges())));b.addView(paragraph("Fida Field pushes queued offline edits first, then downloads current workspace customers, sites, assets, technicians and jobs. A failed sync leaves unsent local changes in the queue."));
        MaterialButton sync=button("Sync now");sync.setEnabled(cloudSync.backendConfigured()&&cloudSync.signedIn()&&accountTeam.hasCloudWorkspace());sync.setOnClickListener(v->runCloud("Synchronizing workspace…",()->cloudSync.syncNow(accountTeam.workspaceId(),accountTeam.canManageTeam()),obj->{CloudSyncFoundation.SyncResult r=(CloudSyncFoundation.SyncResult)obj;refreshEntitlementsAndBranding();toast(r.message);recreate();}));b.addView(sync);
        if(!cloudSync.signedIn()||!accountTeam.hasCloudWorkspace()){b.addView(paragraph("Sign in and bind a cloud workspace under Account & Workspace before synchronization can run."));MaterialButton account=outlineButton("Open Account & Workspace");account.setOnClickListener(v->showAccountWorkspace());b.addView(account);}else{MaterialButton team=outlineButton("Refresh team only");team.setOnClickListener(v->runCloud("Refreshing team…",()->{cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{toast("Team refreshed");showCloudSync();}));b.addView(team);}
        MaterialButton copy=outlineButton("Copy device ID");copy.setOnClickListener(v->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field device ID",cloudSync.deviceId()));toast("Device ID copied");});b.addView(copy);
    }

'''
s = s[:start] + cloud_block + s[end:]
s = s.replace('Fida Field 0.9.8.1 Test\\nAccount, workspace and team-ready offline field service by Fidalix.', 'Fida Field 0.9.9 Test\\nLive Supabase account, workspace and offline-first synchronization by Fidalix.', 1)
main.write_text(s)

readme = Path('fida-field/README.md')
if readme.exists():
    r = readme.read_text().replace('0.9.8.1-test','0.9.9-test').replace('versionCode 11','versionCode 12')
    readme.write_text(r)

print('0.9.9 source transform complete')
