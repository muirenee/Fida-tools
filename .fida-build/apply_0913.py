from pathlib import Path
import re

ROOT = Path('fida-field')

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8')

def once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing patch anchor: {label}')
    return text.replace(old, new, 1)

def regex_once(text, pattern, replacement, label):
    new, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'expected one regex patch for {label}, found {n}')
    return new

# ---------- build/version ----------
p = 'app/build.gradle'
t = read(p)
t = once(t, "versionCode 15", "versionCode 16", 'versionCode')
t = once(t, "versionName '0.9.12-test'", "versionName '0.9.13-test'", 'versionName')
write(p, t)

# ---------- entitlement wording ----------
p = 'app/src/main/java/com/fidalix/fidafield/EntitlementManager.java'
t = read(p)
t = t.replace('return "Verified Google Play subscription";', 'return "Verified company/workspace Google Play subscription";')
write(p, t)

# ---------- local people model ----------
p = 'app/src/main/java/com/fidalix/fidafield/AppDatabase.java'
t = read(p)
t = once(t, 'public static final int DB_VERSION = 7;', 'public static final int DB_VERSION = 8;', 'DB version')
t = once(t,
    'db.execSQL("CREATE TABLE technicians (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT, phone TEXT, email TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL)");',
    'db.execSQL("CREATE TABLE technicians (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT, phone TEXT, email TEXT, user_uuid TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL)");',
    'technicians create')
t = once(t,
    'db.execSQL("CREATE INDEX idx_workspace_invites_workspace ON workspace_invites(workspace_id,status)");',
    'db.execSQL("CREATE INDEX idx_workspace_invites_workspace ON workspace_invites(workspace_id,status)");\n        db.execSQL("CREATE INDEX idx_technicians_user_uuid ON technicians(user_uuid)");',
    'technician user index')
upgrade_anchor = '''        if(oldVersion<7){
            db.execSQL("CREATE TABLE IF NOT EXISTS sync_conflicts (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, remote_uuid TEXT, reason TEXT NOT NULL, detected_at TEXT NOT NULL, UNIQUE(entity_type,entity_id))");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_sync_conflicts_detected ON sync_conflicts(detected_at DESC)");
        }
'''
upgrade_new = upgrade_anchor + '''        if(oldVersion<8){
            db.execSQL("ALTER TABLE technicians ADD COLUMN user_uuid TEXT");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_technicians_user_uuid ON technicians(user_uuid)");
        }
'''
t = once(t, upgrade_anchor, upgrade_new, 'DB v8 migration')

old_tech_methods = '''    public Row getTechnician(long id) { return one("SELECT * FROM technicians WHERE id=?", new String[]{String.valueOf(id)}); }
    public List<Row> technicians() { return rows("SELECT * FROM technicians ORDER BY active DESC,name COLLATE NOCASE", null); }
    public List<Row> activeTechnicians() { return rows("SELECT * FROM technicians WHERE active=1 ORDER BY name COLLATE NOCASE", null); }
    public long saveTechnician(long id, Map<String,String> m) {
        ContentValues v=cv(m,"name","role","phone","email"); putInt(v,"active",m.get("active"));long saved=id;
        if(id==0){v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("technicians",null,v);}else getWritableDatabase().update("technicians",v,"id=?",new String[]{String.valueOf(id)});queueSync("technician",saved,"upsert");return saved;
    }
'''
new_tech_methods = '''    public Row getTechnician(long id) { return one("SELECT * FROM technicians WHERE id=?", new String[]{String.valueOf(id)}); }
    public List<Row> technicians() { return rows("SELECT * FROM technicians ORDER BY active DESC,name COLLATE NOCASE", null); }
    public List<Row> activeTechnicians() { return rows("SELECT * FROM technicians WHERE active=1 ORDER BY name COLLATE NOCASE", null); }
    public Row technicianForUser(String userUuid){if(userUuid==null||userUuid.trim().isEmpty())return new Row();return one("SELECT * FROM technicians WHERE user_uuid=? LIMIT 1",new String[]{userUuid.trim()});}
    public Row workspaceMemberForUser(String workspaceId,String userUuid){if(workspaceId==null||workspaceId.isEmpty()||userUuid==null||userUuid.isEmpty())return new Row();return one("SELECT * FROM workspace_members WHERE workspace_id=? AND user_uuid=? LIMIT 1",new String[]{workspaceId,userUuid});}
    public List<Row> unlinkedWorkspaceMembers(String workspaceId){return rows("SELECT m.* FROM workspace_members m WHERE m.workspace_id=? AND m.status='Active' AND m.user_uuid IS NOT NULL AND m.user_uuid<>'' AND NOT EXISTS (SELECT 1 FROM technicians t WHERE t.user_uuid=m.user_uuid) ORDER BY CASE m.role WHEN 'Owner' THEN 0 WHEN 'Admin' THEN 1 WHEN 'Technician' THEN 2 ELSE 3 END,m.name COLLATE NOCASE",new String[]{workspaceId==null?"":workspaceId});}
    public long saveTechnician(long id, Map<String,String> m) {
        ContentValues v=cv(m,"name","role","phone","email");if(m.containsKey("user_uuid")){String u=m.get("user_uuid");if(u==null||u.trim().isEmpty())v.putNull("user_uuid");else v.put("user_uuid",u.trim());}putInt(v,"active",m.get("active"));long saved=id;
        if(id==0){v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("technicians",null,v);}else getWritableDatabase().update("technicians",v,"id=?",new String[]{String.valueOf(id)});queueSync("technician",saved,"upsert");return saved;
    }
    public void linkTechnicianToMember(long technicianId,long memberId){
        Row tech=getTechnician(technicianId),member=getWorkspaceMember(memberId);if(tech.id()==0||member.id()==0||member.s("user_uuid").isEmpty())return;String user=member.s("user_uuid");
        for(Row old:rows("SELECT id FROM technicians WHERE user_uuid=? AND id<>?",new String[]{user,String.valueOf(technicianId)})){ContentValues clear=new ContentValues();clear.putNull("user_uuid");getWritableDatabase().update("technicians",clear,"id=?",new String[]{String.valueOf(old.id())});queueSync("technician",old.id(),"upsert");}
        ContentValues v=new ContentValues();v.put("user_uuid",user);if(tech.s("email").isEmpty()&&!member.s("email").isEmpty())v.put("email",member.s("email"));if(tech.s("name").isEmpty()&&!member.s("name").isEmpty())v.put("name",member.s("name"));getWritableDatabase().update("technicians",v,"id=?",new String[]{String.valueOf(technicianId)});queueSync("technician",technicianId,"upsert");
    }
    public int autoLinkPeople(String workspaceId){
        if(workspaceId==null||workspaceId.isEmpty())return 0;int linked=0;
        for(Row member:workspaceMembers(workspaceId)){String user=member.s("user_uuid"),email=member.s("email").trim();if(user.isEmpty()||email.isEmpty()||technicianForUser(user).id()>0)continue;List<Row> candidates=rows("SELECT * FROM technicians WHERE (user_uuid IS NULL OR user_uuid='') AND email<>'' AND lower(trim(email))=lower(trim(?))",new String[]{email});if(candidates.size()==1){linkTechnicianToMember(candidates.get(0).id(),member.id());linked++;}}
        return linked;
    }
'''
t = once(t, old_tech_methods, new_tech_methods, 'technician methods')

# Auto-link cached cloud members after refresh.
t = once(t,
    '            d.delete("sync_queue","entity_type IN (\'workspace_member\',\'workspace_invite\')",null);d.setTransactionSuccessful();}finally{d.endTransaction();}\n    }\n    private String j(JSONObject o,String k)',
    '            d.delete("sync_queue","entity_type IN (\'workspace_member\',\'workspace_invite\')",null);d.setTransactionSuccessful();}finally{d.endTransaction();}\n        autoLinkPeople(workspaceId);\n    }\n    private String j(JSONObject o,String k)',
    'cache team auto-link')

old_remote_tech = 'else if("technician".equals(type)){jt(v,o,"name","role","phone","email");v.put("active",o.optBoolean("active",true)?1:0);if(local==0){v.put("created_at",now());local=d.insertOrThrow("technicians",null,v);}else d.update("technicians",v,"id=?",new String[]{String.valueOf(local)});}'
new_remote_tech = 'else if("technician".equals(type)){String linkedUser=j(o,"user_id");if(local==0&&!linkedUser.isEmpty())local=technicianForUser(linkedUser).id();jt(v,o,"name","role","phone","email");if(linkedUser.isEmpty())v.putNull("user_uuid");else v.put("user_uuid",linkedUser);v.put("active",o.optBoolean("active",true)?1:0);if(local==0){v.put("created_at",now());local=d.insertOrThrow("technicians",null,v);}else d.update("technicians",v,"id=?",new String[]{String.valueOf(local)});}'
t = once(t, old_remote_tech, new_remote_tech, 'remote technician link')
write(p, t)

# ---------- cloud sync sends the person/member link ----------
p = 'app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java'
t = read(p)
old = 'else if("technician".equals(type)){copy(o,r,"name","role","phone","email");o.put("active",r.i("active")==1);}'
new = 'else if("technician".equals(type)){copy(o,r,"name","role","phone","email");String user=r.s("user_uuid");if(user.isEmpty())o.put("user_id",JSONObject.NULL);else o.put("user_id",user);o.put("active",r.i("active")==1);}'
t = once(t, old, new, 'technician cloud payload')
write(p, t)

# ---------- workspace-scoped Google Play billing ----------
p = 'app/src/main/java/com/fidalix/fidafield/BillingManager.java'
t = read(p)
t = once(t,
    '    public String subscriptionState(){return prefs.getString("subscription_state","");}\n',
    '    public String subscriptionState(){return prefs.getString("subscription_state","");}\n    private String workspaceId(){return prefs.getString(AccountTeamManager.KEY_WORKSPACE_ID,"");}\n    private boolean hasCloudWorkspace(){return prefs.getBoolean(AccountTeamManager.KEY_CLOUD_WORKSPACE_BOUND,false)&&!workspaceId().isEmpty();}\n    private boolean canManageBilling(){String r=prefs.getString(AccountTeamManager.KEY_ACCOUNT_ROLE,"");return AccountTeamManager.ROLE_OWNER.equals(r)||AccountTeamManager.ROLE_ADMIN.equals(r);}\n',
    'billing workspace helpers')
t = once(t,
    '        if(!supabase.hasStoredSession()){setResult("Sign in to your Fida Field account before subscribing");return;}\n        if(billingClient==null||!ready){',
    '        if(!supabase.hasStoredSession()){setResult("Sign in to your Fida Field account before subscribing");return;}\n        if(!hasCloudWorkspace()){setResult("Create or join a cloud workspace before subscribing");return;}\n        if(!canManageBilling()){setResult("Only a workspace Owner or Admin can manage the company subscription");return;}\n        if(billingClient==null||!ready){',
    'purchase workspace guard')
t = once(t,
    'JSONObject body=new JSONObject().put("package_name",BuildConfig.APPLICATION_ID).put("product_id",productId).put("purchase_token",token);',
    'JSONObject body=new JSONObject().put("package_name",BuildConfig.APPLICATION_ID).put("workspace_id",workspaceId()).put("product_id",productId).put("purchase_token",token);',
    'workspace verify body')
t = t.replace('"Verified Pro subscription"', '"Verified workspace Pro subscription"')

new_refresh = '''    public void refreshServerEntitlement(){
        if(BuildConfig.OPEN_EDITION)return;
        if(!supabase.hasStoredSession()||!hasCloudWorkspace()){
            prefs.edit().putBoolean("subscription_pro_enabled",false).apply();notifyChanged();return;
        }
        new Thread(()->{
            try{
                String workspace=workspaceId();
                JSONArray a=supabase.select("workspace_billing_entitlements","select=active,product_id,subscription_state,expires_at,last_verified_at,purchaser_user_id&workspace_id=eq."+workspace+"&limit=1");
                if(a.length()==0){prefs.edit().putBoolean("subscription_pro_enabled",false).putString("billing_last_result","No verified Pro plan for this workspace").apply();}
                else{
                    JSONObject o=a.getJSONObject(0);boolean active=o.optBoolean("active",false);String expiry=o.optString("expires_at","");
                    if(active&&!expiry.isEmpty()){try{active=java.time.Instant.parse(expiry).isAfter(java.time.Instant.now());}catch(Exception ignored){}}
                    prefs.edit().putBoolean("subscription_pro_enabled",active).putString("subscription_product_id",o.optString("product_id","")).putString("subscription_state",o.optString("subscription_state","")).putString("subscription_expires_at",expiry).putString("billing_last_result",active?"Workspace Pro plan active":"No active Pro plan for this workspace").apply();
                }
                main.post(this::notifyChanged);
            }catch(Exception e){setResultFromBackground("Workspace entitlement refresh failed · "+safe(e));}
        },"fida-entitlement-refresh").start();
    }
'''
t = regex_once(t, r'    public void refreshServerEntitlement\(\)\{.*?\n    \}\n\n    private void setResult', new_refresh + '\n    private void setResult', 'workspace entitlement refresh')
write(p, t)

# ---------- unified People & Team UI + workspace billing explanation ----------
p = 'app/src/main/java/com/fidalix/fidafield/MainActivity.java'
t = read(p)
t = t.replace('Fida Field 0.9.12 Test', 'Fida Field 0.9.13 Test')
t = t.replace('For this test build you can enable Pro under More → Plan & subscription.', 'Use More → Plan & subscription to subscribe the company workspace. Fidalix Open builds are enabled internally without Google Play Billing.')

new_people = r'''    private void showPeopleTeam(){
        setHeader("People & Team","One person · job assignment · app access");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        b.addView(paragraph("Each person is shown once. Job assignment and workspace/app access are separate capabilities: a contractor can be field-only with no app, while a signed-in member can optionally be made available for field jobs."));
        if(accountTeam.hasWorkspace())db.autoLinkPeople(accountTeam.workspaceId());
        boolean cloud=accountTeam.hasCloudWorkspace()&&cloudSync.signedIn();
        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton add=button("+ Field-only person");add.setOnClickListener(v->showUnifiedPerson(0,0));actions.addView(add,new LinearLayout.LayoutParams(0,dp(52),1));if(accountTeam.hasWorkspace()&&accountTeam.canManageTeam()){actions.addView(spacerH());MaterialButton invite=outlineButton("+ App access");invite.setOnClickListener(v->showInviteDialog());actions.addView(invite,new LinearLayout.LayoutParams(0,dp(52),1));}b.addView(actions);
        if(accountTeam.hasWorkspace()){b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Your access role",accountTeam.accountRole()));if(cloud){MaterialButton refresh=outlineButton("Refresh people & access");refresh.setOnClickListener(v->runCloud("Refreshing people…",()->{cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{db.autoLinkPeople(accountTeam.workspaceId());toast("People refreshed");showPeopleTeam();}));b.addView(refresh);}}

        b.addView(section("People"));
        java.util.HashSet<Long> shownTechs=new java.util.HashSet<>();int shown=0;
        if(accountTeam.hasWorkspace()){
            for(AppDatabase.Row m:db.workspaceMembers(accountTeam.workspaceId())){AppDatabase.Row tech=db.technicianForUser(m.s("user_uuid"));if(tech.id()>0)shownTechs.add(tech.id());String field=tech.id()>0?(tech.i("active")==1?"Field active":"Field inactive"):"Not assigned to field jobs";String detail=tech.id()>0?(tech.s("role").isEmpty()?"Field technician":tech.s("role"))+(tech.s("phone").isEmpty()?"":" • "+tech.s("phone")):(m.s("email").isEmpty()?"Workspace member":m.s("email"));MaterialCardView c=rowCard(m.s("name"),detail,m.s("role")+" · "+field);long mid=m.id(),tid=tech.id();c.setOnClickListener(v->showUnifiedPerson(mid,tid));b.addView(c);shown++;}
        }
        for(AppDatabase.Row tech:db.technicians()){if(shownTechs.contains(tech.id()))continue;AppDatabase.Row linked=accountTeam.hasWorkspace()?db.workspaceMemberForUser(accountTeam.workspaceId(),tech.s("user_uuid")):new AppDatabase.Row();if(linked.id()>0)continue;String detail=(tech.s("role").isEmpty()?"Field technician":tech.s("role"))+(tech.s("email").isEmpty()?"":" • "+tech.s("email"))+(tech.s("phone").isEmpty()?"":" • "+tech.s("phone"));MaterialCardView c=rowCard(tech.s("name"),detail,"No app access · "+(tech.i("active")==1?"Field active":"Field inactive"));long tid=tech.id();c.setOnClickListener(v->showUnifiedPerson(0,tid));b.addView(c);shown++;}
        if(shown==0)b.addView(empty("No people yet. Add a field-only person or invite someone who needs app access."));

        if(accountTeam.hasWorkspace()){
            List<AppDatabase.Row> invites=db.workspaceInvites(accountTeam.workspaceId());b.addView(section("Pending app invitations"));if(invites.isEmpty())b.addView(empty("No pending invitations."));
            for(AppDatabase.Row r:invites){MaterialCardView c=rowCard(r.s("email"),r.s("role"),r.s("status"));if("Pending".equals(r.s("status")))c.setOnClickListener(v->{String code=r.s("token");MaterialAlertDialogBuilder d=new MaterialAlertDialogBuilder(this).setTitle("Pending invitation").setMessage(r.s("email")+" · "+r.s("role")+(code.isEmpty()?"":"\n\nInvitation code:\n"+code)+(r.s("expires_at").isEmpty()?"":"\nExpires: "+r.s("expires_at"))).setNegativeButton("Close",null);if(!code.isEmpty())d.setNeutralButton("Copy code",(x,w)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",code));toast("Invitation code copied");});if(accountTeam.canManageTeam())d.setPositiveButton("Cancel invitation",(x,w)->{if(cloud)runCloud("Cancelling invitation…",()->{cloudSync.cancelInvite(r.s("invite_uuid"));cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return null;},z->{toast("Invitation cancelled");showPeopleTeam();});else{db.cancelWorkspaceInvite(r.id());showPeopleTeam();}});d.show();});b.addView(c);}
        }
    }

    private void showUnifiedPerson(long memberId,long technicianId){
        AppDatabase.Row member=memberId>0?db.getWorkspaceMember(memberId):new AppDatabase.Row();AppDatabase.Row tech=technicianId>0?db.getTechnician(technicianId):new AppDatabase.Row();boolean hasMember=member.id()>0,hasTech=tech.id()>0;
        LinearLayout f=form();String personName=hasTech?tech.s("name"):member.s("name");String personEmail=hasTech&&!tech.s("email").isEmpty()?tech.s("email"):member.s("email");EditText name=input("Person name *",personName);EditText fieldRole=input("Field role / job title",hasTech?tech.s("role"):"");EditText phone=input("Phone",hasTech?tech.s("phone"):"");EditText email=input("Email",personEmail);MaterialSwitch field=new MaterialSwitch(this);field.setText("Available for field job assignment");field.setChecked(hasTech&&tech.i("active")==1);f.addView(name);f.addView(fieldRole);f.addView(phone);f.addView(email);f.addView(field);
        if(hasMember){f.addView(section("Workspace access"));f.addView(info("Access role",member.s("role")));f.addView(info("Access status",member.s("status")));if(accountTeam.canManageTeam()&&!"Owner".equals(member.s("role"))){MaterialButton access=outlineButton("Manage workspace access");access.setOnClickListener(v->showMemberDialog(memberId));f.addView(access);}}
        if(!hasMember&&hasTech&&accountTeam.hasWorkspace()&&accountTeam.canManageTeam()){f.addView(section("App access"));List<AppDatabase.Row> linkable=db.unlinkedWorkspaceMembers(accountTeam.workspaceId());if(!linkable.isEmpty()){MaterialButton link=outlineButton("Link existing workspace member");link.setOnClickListener(v->showLinkMemberDialog(technicianId));f.addView(link);}MaterialButton invite=outlineButton("Invite this person to workspace");invite.setEnabled(!val(email).isEmpty());invite.setOnClickListener(v->showInviteDialog(val(email),AccountTeamManager.ROLE_TECHNICIAN));f.addView(invite);}
        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle(hasMember||hasTech?"Person profile":"Add field-only person").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Name required");return;}if(!val(email).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(email)).matches()){email.setError("Enter a valid email");return;}String user=hasMember?member.s("user_uuid"):tech.s("user_uuid");if(field.isChecked()||hasTech){db.saveTechnician(technicianId,AppDatabase.map("name",val(name),"role",val(fieldRole),"phone",val(phone),"email",val(email),"user_uuid",user,"active",field.isChecked()?"1":"0"));}d.dismiss();toast(field.isChecked()?"Person available for field jobs":"Person profile saved");showPeopleTeam();}));d.show();
    }

    private void showLinkMemberDialog(long technicianId){
        if(!accountTeam.hasWorkspace())return;List<AppDatabase.Row> members=db.unlinkedWorkspaceMembers(accountTeam.workspaceId());if(members.isEmpty()){toast("No unlinked workspace members available");return;}String[] labels=new String[members.size()];for(int i=0;i<members.size();i++){AppDatabase.Row m=members.get(i);labels[i]=m.s("name")+(m.s("email").isEmpty()?"":" · "+m.s("email"))+" · "+m.s("role");}new MaterialAlertDialogBuilder(this).setTitle("Link to workspace member").setItems(labels,(d,which)->{db.linkTechnicianToMember(technicianId,members.get(which).id());toast("Person linked to workspace access");showPeopleTeam();}).setNegativeButton("Cancel",null).show();
    }

    private void showTechnicians'''
t = regex_once(t, r'    private void showPeopleTeam\(\)\{.*?\n    \}\n\n    private void showTechnicians', new_people, 'unified People & Team')

new_invite = r'''    private void showInviteDialog(){showInviteDialog("",AccountTeamManager.ROLE_TECHNICIAN);}
    private void showInviteDialog(String prefillEmail,String defaultRole){
        if(!accountTeam.canManageTeam()){toast("Owner or Admin access required");return;}LinearLayout f=form();EditText email=input("Email address",prefillEmail==null?"":prefillEmail);Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});setSpinner(role,defaultRole==null?AccountTeamManager.ROLE_TECHNICIAN:defaultRole);f.addView(email);f.addView(label("Role"));f.addView(role);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Invite workspace member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Create invitation",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String e=val(email),r=String.valueOf(role.getSelectedItem());if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){runCloud("Creating invitation…",()->{String token=cloudSync.createInvite(accountTeam.workspaceId(),e,r);cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return token;},obj->{d.dismiss();String token=String.valueOf(obj);new MaterialAlertDialogBuilder(this).setTitle("Invitation created").setMessage("Share this code with "+e+". After they join, Fida Field will automatically link the account to a matching field profile when the email is the same.\n\n"+token).setNegativeButton("Close",(a,b)->showPeopleTeam()).setPositiveButton("Copy code",(a,b)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",token));toast("Invitation code copied");showPeopleTeam();}).show();});}else{db.saveWorkspaceInvite(accountTeam.workspaceId(),e,r);d.dismiss();toast("Invitation saved locally");showPeopleTeam();}}));d.show();
    }

    private void showMemberDialog'''
t = regex_once(t, r'    private void showInviteDialog\(\)\{.*?\n    \}\n\n    private void showMemberDialog', new_invite, 'prefilled invitations')

new_plan = r'''    private void showPlan(){
        setHeader("Plan & Subscription",BuildConfig.OPEN_EDITION?"Fidalix internal edition":"Company workspace subscription");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        refreshEntitlementsAndBranding();
        b.addView(section("Current plan"));b.addView(info("Plan",entitlements.planName()));b.addView(info("Entitlement",entitlements.entitlementSource()));b.addView(info("Subscription scope",BuildConfig.OPEN_EDITION?"Internal Fidalix build":"Company / workspace"));b.addView(info("Monthly usage",entitlements.usageSummary()));
        if(BuildConfig.OPEN_EDITION){
            b.addView(section("Fidalix Open"));b.addView(paragraph("This internal company edition does not use Google Play Billing. Pro capabilities are permanently enabled by the signed build itself, while cloud accounts, workspace security and Supabase synchronization continue to work normally. Keep this APK for authorized internal distribution."));b.addView(info("Billing","Not required"));b.addView(info("Distribution","Direct/internal APK"));return;
        }
        b.addView(info("Free allowance",EntitlementManager.FREE_MONTHLY_REPORT_LIMIT+" new service reports / month"));
        b.addView(section("Google Play Pro · workspace plan"));b.addView(paragraph("One verified subscription upgrades the company workspace, not one phone. The Owner or an Admin purchases through Google Play; every active member of that workspace inherits the Pro plan on their own Android device after signing in and refreshing the workspace entitlement."));
        b.addView(info("Billing status",billingManager==null?"Initializing":billingManager.lastResult()));b.addView(info("Subscription state",billingManager==null||billingManager.subscriptionState().isEmpty()?"Not verified":billingManager.subscriptionState()));b.addView(info("Expires",billingManager==null||billingManager.expiry().isEmpty()?"—":billingManager.expiry()));
        boolean readyAccount=cloudSync.signedIn()&&accountTeam.hasCloudWorkspace();boolean manager=readyAccount&&accountTeam.canManageTeam();
        if(!readyAccount){b.addView(paragraph("Sign in and create or join a cloud workspace first. Subscriptions are attached to the company workspace rather than to this device."));MaterialButton account=outlineButton("Open Account & Workspace");account.setOnClickListener(v->showAccountWorkspace());b.addView(account);}else if(!manager){b.addView(paragraph("Your workspace role is "+accountTeam.accountRole()+". You inherit the company plan automatically; only an Owner or Admin needs to purchase or manage billing."));}
        String monthly=billingManager==null?"Not loaded":billingManager.displayPrice(EntitlementManager.PRODUCT_PRO_MONTHLY);String annual=billingManager==null?"Not loaded":billingManager.displayPrice(EntitlementManager.PRODUCT_PRO_ANNUAL);
        if(manager){MaterialButton buyMonthly=button("Monthly workspace Pro · "+monthly);buyMonthly.setOnClickListener(v->{if(billingManager!=null)billingManager.purchase(this,EntitlementManager.PRODUCT_PRO_MONTHLY);});b.addView(buyMonthly);MaterialButton buyAnnual=button("Annual workspace Pro · "+annual);buyAnnual.setOnClickListener(v->{if(billingManager!=null)billingManager.purchase(this,EntitlementManager.PRODUCT_PRO_ANNUAL);});b.addView(buyAnnual);MaterialButton restore=outlineButton("Restore purchaser's Google Play subscription");restore.setOnClickListener(v->{if(billingManager!=null){billingManager.restore();toast("Checking Google Play purchase…");}});b.addView(restore);}
        MaterialButton refresh=outlineButton("Refresh workspace plan");refresh.setEnabled(readyAccount);refresh.setOnClickListener(v->{if(billingManager!=null){billingManager.refreshServerEntitlement();toast("Refreshing workspace entitlement…");}});b.addView(refresh);
        b.addView(paragraph("Field-only people who do not sign in do not consume a separate app subscription. Workspace members can install Fida Field on their own devices and use the same company plan according to their access role."));
    }

    private void showBranding'''
t = regex_once(t, r'    private void showPlan\(\)\{.*?\n    \}\n\n    private void showBranding', new_plan, 'workspace plan UI')

# Preserve an existing user link when using the legacy technician editor.
t = t.replace('"email",val(email),"active","Active".equals(String.valueOf(active.getSelectedItem()))?"1":"0"', '"email",val(email),"user_uuid",r.s("user_uuid"),"active","Active".equals(String.valueOf(active.getSelectedItem()))?"1":"0"')
write(p, t)

print('0.9.13 migration staged successfully')
