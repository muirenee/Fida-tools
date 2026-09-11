from pathlib import Path
import re


def replace_once(text, old, new, label):
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)


def regex_once(text, pattern, replacement, label, flags=re.S):
    out, n = re.subn(pattern, lambda m: replacement, text, count=1, flags=flags)
    if n != 1:
        raise AssertionError(f"regex anchor mismatch {label}: {n}")
    return out

# --- Android deep link for workspace invitation ---
p = Path('fida-field/app/src/main/AndroidManifest.xml')
s = p.read_text()
launcher = '''            <intent-filter>\n                <action android:name="android.intent.action.MAIN" />\n                <category android:name="android.intent.category.LAUNCHER" />\n            </intent-filter>'''
invite_filter = launcher + '''\n            <intent-filter>\n                <action android:name="android.intent.action.VIEW" />\n                <category android:name="android.intent.category.DEFAULT" />\n                <category android:name="android.intent.category.BROWSABLE" />\n                <data android:scheme="fidafield" android:host="workspace-invite" />\n            </intent-filter>'''
s = replace_once(s, launcher, invite_filter, 'manifest invite intent filter')
p.write_text(s)

# --- Main activity: invite onboarding + role-sensitive UI ---
p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = p.read_text()

s = replace_once(s,
'''        buildChrome();\n        showDashboard();\n    }\n\n    @Override protected void onResume(){super.onResume();if(billingManager!=null)billingManager.refreshPurchases();}\n    @Override protected void onDestroy(){if(billingManager!=null)billingManager.stop();super.onDestroy();}''',
'''        buildChrome();\n        if(captureWorkspaceInviteIntent(getIntent())||hasPendingWorkspaceInvite())showAccountWorkspace();else showDashboard();\n    }\n\n    @Override protected void onResume(){super.onResume();if(billingManager!=null)billingManager.refreshPurchases();}\n    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);if(captureWorkspaceInviteIntent(intent))showAccountWorkspace();}\n    @Override protected void onDestroy(){if(billingManager!=null)billingManager.stop();super.onDestroy();}\n\n    private static final String KEY_PENDING_INVITE_TOKEN="pending_workspace_invite_token";\n    private static final String KEY_PENDING_INVITE_EMAIL="pending_workspace_invite_email";\n    private boolean captureWorkspaceInviteIntent(Intent intent){\n        Uri data=intent==null?null:intent.getData();if(data==null||!"fidafield".equalsIgnoreCase(data.getScheme())||!"workspace-invite".equalsIgnoreCase(data.getHost()))return false;\n        String token=data.getQueryParameter("token"),email=data.getQueryParameter("email");if(token==null||token.trim().isEmpty())return false;\n        prefs.edit().putString(KEY_PENDING_INVITE_TOKEN,token.trim()).putString(KEY_PENDING_INVITE_EMAIL,email==null?"":email.trim()).apply();return true;\n    }\n    private boolean hasPendingWorkspaceInvite(){return !prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim().isEmpty();}\n    private String pendingWorkspaceInviteToken(){return prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim();}\n    private String pendingWorkspaceInviteEmail(){return prefs.getString(KEY_PENDING_INVITE_EMAIL,"").trim();}\n    private void clearPendingWorkspaceInvite(){prefs.edit().remove(KEY_PENDING_INVITE_TOKEN).remove(KEY_PENDING_INVITE_EMAIL).apply();}''',
'onCreate invite routing')

s = replace_once(s,
'''    private boolean canSeeAllJobs(){return accountTeam!=null&&accountTeam.canManageTeam();}\n    private String currentJobUserUuid(){return accountTeam==null?"":accountTeam.cloudUserId();}''',
'''    private boolean canSeeAllJobs(){return accountTeam!=null&&accountTeam.canManageTeam();}\n    private boolean canManageWorkspaceSettings(){return accountTeam==null||!accountTeam.hasWorkspace()||accountTeam.canManageTeam();}\n    private boolean canPerformFieldWork(){if(accountTeam==null||!accountTeam.hasWorkspace())return true;String r=accountTeam.accountRole();return AccountTeamManager.ROLE_OWNER.equals(r)||AccountTeamManager.ROLE_ADMIN.equals(r)||AccountTeamManager.ROLE_TECHNICIAN.equals(r);}\n    private boolean requireWorkspaceManager(String feature){if(canManageWorkspaceSettings())return true;new MaterialAlertDialogBuilder(this).setTitle("Owner or Admin only").setMessage(feature+" can only be changed by a workspace Owner or Admin. Your "+accountTeam.accountRole()+" account remains focused on assigned service work.").setPositiveButton("OK",null).show();return false;}\n    private String currentJobUserUuid(){return accountTeam==null?"":accountTeam.cloudUserId();}''',
'role helpers')

s = replace_once(s,
'''        brandingLogoLauncher=registerForActivityResult(new ActivityResultContracts.GetContent(), uri->{\n            if(uri==null)return;\n            if(!entitlements.canUseCustomBranding()){showUpgradeRequired("Custom branding");return;}''',
'''        brandingLogoLauncher=registerForActivityResult(new ActivityResultContracts.GetContent(), uri->{\n            if(uri==null)return;\n            if(!requireWorkspaceManager("Custom branding"))return;\n            if(!entitlements.canUseCustomBranding()){showUpgradeRequired("Custom branding");return;}''',
'branding picker guard')

s = replace_once(s,
'''        b.addView(section("Quick actions"));LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton newJob=button("+ New job");newJob.setOnClickListener(v->showJobDialog(0,0));actions.addView(newJob,new LinearLayout.LayoutParams(0,dp(52),1));actions.addView(spacerH());MaterialButton newClient=outlineButton("+ Customer");newClient.setOnClickListener(v->showCustomerDialog(0));actions.addView(newClient,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(actions);''',
'''        b.addView(section("Quick actions"));LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);if(canPerformFieldWork()){MaterialButton newJob=button("+ New job");newJob.setOnClickListener(v->showJobDialog(0,0));actions.addView(newJob,new LinearLayout.LayoutParams(0,dp(52),1));}if(canManageWorkspaceSettings()){if(actions.getChildCount()>0)actions.addView(spacerH());MaterialButton newClient=outlineButton("+ Customer");newClient.setOnClickListener(v->showCustomerDialog(0));actions.addView(newClient,new LinearLayout.LayoutParams(0,dp(52),1));}if(actions.getChildCount()>0)b.addView(actions);else b.addView(paragraph("Viewer access is read-only."));''',
'dashboard quick actions')

s = replace_once(s,
'''        MaterialButton add=button("+ New service job");add.setOnClickListener(v->showJobDialog(0,0));b.addView(add,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(52)));''',
'''        if(canPerformFieldWork()){MaterialButton add=button("+ New service job");add.setOnClickListener(v->showJobDialog(0,0));b.addView(add,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(52)));}else b.addView(paragraph("Viewer access is read-only. You can review jobs available to your account."));''',
'jobs create guard')

s = replace_once(s,
'''        LinearLayout a=new LinearLayout(this);a.setOrientation(LinearLayout.HORIZONTAL);MaterialButton cbtn=button("+ Customer");cbtn.setOnClickListener(v->showCustomerDialog(0));a.addView(cbtn,new LinearLayout.LayoutParams(0,dp(52),1));a.addView(spacerH());MaterialButton sbtn=outlineButton("+ Site");sbtn.setOnClickListener(v->showSiteDialog(0,0));a.addView(sbtn,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(a);''',
'''        if(canManageWorkspaceSettings()){LinearLayout a=new LinearLayout(this);a.setOrientation(LinearLayout.HORIZONTAL);MaterialButton cbtn=button("+ Customer");cbtn.setOnClickListener(v->showCustomerDialog(0));a.addView(cbtn,new LinearLayout.LayoutParams(0,dp(52),1));a.addView(spacerH());MaterialButton sbtn=outlineButton("+ Site");sbtn.setOnClickListener(v->showSiteDialog(0,0));a.addView(sbtn,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(a);}else b.addView(paragraph("Customer and site master data is read-only for "+accountTeam.accountRole()+" accounts."));''',
'customers manager actions')

old = '''        AppDatabase.Row c=db.getCustomer(id);if(c.id()==0){toast("Customer not found");return;}setHeader(c.s("name"),"Customer service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showCustomerDialog(id));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));b.addView(top);'''
new = '''        AppDatabase.Row c=db.getCustomer(id);if(c.id()==0){toast("Customer not found");return;}setHeader(c.s("name"),"Customer service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showCustomerDialog(id));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);'''
s = replace_once(s, old, new, 'customer detail edit')
s = replace_once(s,
'''        MaterialButton addSite=button("+ Add service site");addSite.setOnClickListener(v->showSiteDialog(0,id));b.addView(addSite);''',
'''        if(canManageWorkspaceSettings()){MaterialButton addSite=button("+ Add service site");addSite.setOnClickListener(v->showSiteDialog(0,id));b.addView(addSite);}''',
'customer add site')

old = '''        AppDatabase.Row s=db.getSite(id);if(s.id()==0){toast("Site not found");return;}AppDatabase.Row c=db.getCustomer(parse(s.s("customer_id")));setHeader(s.s("name"),"Site service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showSiteDialog(id,parse(s.s("customer_id"))));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));b.addView(top);'''
new = '''        AppDatabase.Row s=db.getSite(id);if(s.id()==0){toast("Site not found");return;}AppDatabase.Row c=db.getCustomer(parse(s.s("customer_id")));setHeader(s.s("name"),"Site service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showSiteDialog(id,parse(s.s("customer_id"))));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);'''
s = replace_once(s, old, new, 'site detail edit')

s = replace_once(s,
'''        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton add=button("+ Add asset");add.setOnClickListener(v->showAssetDialog(0));actions.addView(add,new LinearLayout.LayoutParams(0,dp(52),1));actions.addView(spacerH());MaterialButton scan=outlineButton("Scan QR");scan.setOnClickListener(v->scanAssetQr());actions.addView(scan,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(actions);''',
'''        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);if(canManageWorkspaceSettings()){MaterialButton add=button("+ Add asset");add.setOnClickListener(v->showAssetDialog(0));actions.addView(add,new LinearLayout.LayoutParams(0,dp(52),1));actions.addView(spacerH());}MaterialButton scan=outlineButton("Scan QR");scan.setOnClickListener(v->scanAssetQr());actions.addView(scan,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(actions);''',
'asset list manager action')

s = regex_once(s,
 r'''    private void showMore\(\)\{.*?\n    \}\n\n    private void showReports\(\)\{''',
'''    private void showMore(){\n        currentMenu=MENU_MORE;bottom.getMenu().findItem(MENU_MORE).setChecked(true);setHeader("More","Reports, maintenance & settings");clear();LinearLayout b=body(page());\n        b.addView(brandPanel());\n        b.addView(section("Workspace"));\n        b.addView(menuCard("PDF reports","Generate and share completed service reports",v->showReports()));\n        b.addView(menuCard("Maintenance planner","Assets due, overdue and recurring service",v->showMaintenance()));\n        if(canManageWorkspaceSettings()){\n            b.addView(menuCard("People & Team",db.technicians().size()+" field technicians • "+accountTeam.teamSummary(),v->showPeopleTeam()));\n            b.addView(menuCard("Backup & restore","Export or restore all local business data",v->showBackup()));\n        }\n        b.addView(menuCard("Plan & subscription",entitlements.planName()+" • "+entitlements.usageSummary(),v->showPlan()));\n        if(canManageWorkspaceSettings())b.addView(menuCard("Custom branding · Pro",entitlements.isPro()?(branding.isActive()?"Active custom company identity":"Logo, colors and branded PDFs"):"Subscriber feature · upgrade to unlock",v->{if(entitlements.canUseCustomBranding())showBranding();else showUpgradeRequired("Custom branding");}));\n        b.addView(menuCard("Account & workspace",accountTeam.hasWorkspace()?accountTeam.workspaceName()+" • "+accountTeam.accountRole():"Set up account and workspace",v->showAccountWorkspace()));\n        b.addView(menuCard("Cloud & team sync",cloudSync.backendStatus()+" • "+cloudSync.pendingChanges()+" pending",v->showCloudSync()));\n        if(canManageWorkspaceSettings())b.addView(menuCard("Company settings","Company identity, report numbering and application preferences",v->showSettings()));\n        else b.addView(paragraph(accountTeam.accountRole()+" access: work with assigned service jobs and operational data. Company settings, team administration, branding, backups and master-data changes are restricted to Owner/Admin."));\n        b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.17 Test\\nSimplified invitation onboarding and workspace role security by Fidalix."));\n    }\n\n    private void showReports(){''',
'showMore role menu')

s = replace_once(s,
'''        b.addView(section("Data exports"));LinearLayout exports=new LinearLayout(this);exports.setOrientation(LinearLayout.HORIZONTAL);MaterialButton jobsCsv=outlineButton("Jobs CSV · Pro");jobsCsv.setOnClickListener(v->{if(entitlements.canExportCsv())shareCsv("jobs");else showUpgradeRequired("CSV export");});exports.addView(jobsCsv,new LinearLayout.LayoutParams(0,dp(50),1));exports.addView(spacerH());MaterialButton assetsCsv=outlineButton("Assets CSV · Pro");assetsCsv.setOnClickListener(v->{if(entitlements.canExportCsv())shareCsv("assets");else showUpgradeRequired("CSV export");});exports.addView(assetsCsv,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(exports);b.addView(paragraph("CSV exports can be opened in Excel, Google Sheets or attached to customer/project records."));''',
'''        if(canManageWorkspaceSettings()){b.addView(section("Data exports"));LinearLayout exports=new LinearLayout(this);exports.setOrientation(LinearLayout.HORIZONTAL);MaterialButton jobsCsv=outlineButton("Jobs CSV · Pro");jobsCsv.setOnClickListener(v->{if(entitlements.canExportCsv())shareCsv("jobs");else showUpgradeRequired("CSV export");});exports.addView(jobsCsv,new LinearLayout.LayoutParams(0,dp(50),1));exports.addView(spacerH());MaterialButton assetsCsv=outlineButton("Assets CSV · Pro");assetsCsv.setOnClickListener(v->{if(entitlements.canExportCsv())shareCsv("assets");else showUpgradeRequired("CSV export");});exports.addView(assetsCsv,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(exports);b.addView(paragraph("Workspace data exports are restricted to Owner/Admin."));}''',
'CSV exports manager only')

for sig, feature in [
    ('private void showBackup(){','Backup & restore'),
    ('private void showSettings(){','Company settings'),
    ('private void showCustomerDialog(long id){','Customer master data'),
    ('private void showSiteDialog(long id,long preferredCustomer){','Site master data'),
    ('private void showAssetDialog(long id){','Asset master data'),
    ('private void showPeopleTeam(){','People & Team'),
    ('private void showTeam(){','Team administration'),
    ('private void showTechnicians(){','Technician administration'),
    ('private void showTechnicianDialog(long id){','Technician administration'),
    ('private void showUnifiedPerson(long memberId,long technicianId){','People & Team'),
    ('private void showLinkMemberDialog(long technicianId){','People & Team'),
    ('private void showMemberDialog(long id){','Team administration'),
]:
    s = replace_once(s, '    '+sig+'\n', '    '+sig+'\n        if(!requireWorkspaceManager("'+feature+'"))return;\n', sig)

s = replace_once(s,
'''    private void showBranding(){\n        if(!entitlements.canUseCustomBranding()){showUpgradeRequired("Custom branding");return;}''',
'''    private void showBranding(){\n        if(!requireWorkspaceManager("Custom branding"))return;\n        if(!entitlements.canUseCustomBranding()){showUpgradeRequired("Custom branding");return;}''',
'branding manager guard')

s = replace_once(s,
'''    private void showJobDialog(long id,long preferredAsset){\n        if(id==0&&!entitlements.canCreateReport()){showUpgradeRequired("More service reports");return;}''',
'''    private void showJobDialog(long id,long preferredAsset){\n        if(!canPerformFieldWork()){new MaterialAlertDialogBuilder(this).setTitle("Read-only access").setMessage("Viewer accounts can review available service information but cannot create or modify jobs.").setPositiveButton("OK",null).show();return;}\n        if(id==0&&!entitlements.canCreateReport()){showUpgradeRequired("More service reports");return;}''',
'viewer job guard')
s = replace_once(s,
'''boolean completed="Completed".equals(j.s("status"));boolean canModify=!completed||accountTeam.canManageTeam();''',
'''boolean completed="Completed".equals(j.s("status"));boolean canModify=canPerformFieldWork()&&(!completed||accountTeam.canManageTeam());''',
'job modification role')
s = replace_once(s,
'''if(!"Completed".equals(j.s("status"))){MaterialButton complete=outlineButton("Mark job completed");''',
'''if(canModify&&!"Completed".equals(j.s("status"))){MaterialButton complete=outlineButton("Mark job completed");''',
'job completion role')

old = '''        AppDatabase.Row a=db.getAsset(id);if(a.id()==0){toast("Asset not found");return;}setHeader(a.s("tag"),"Asset service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Assets");back.setOnClickListener(v->showAssets());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showAssetDialog(id));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));b.addView(top);'''
new = '''        AppDatabase.Row a=db.getAsset(id);if(a.id()==0){toast("Asset not found");return;}setHeader(a.s("tag"),"Asset service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Assets");back.setOnClickListener(v->showAssets());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showAssetDialog(id));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);'''
s = replace_once(s, old, new, 'asset detail edit')
s = replace_once(s,
'''        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton job=button("+ Service job");job.setOnClickListener(v->showJobDialog(0,id));actions.addView(job,new LinearLayout.LayoutParams(0,dp(50),1));actions.addView(spacerH());MaterialButton qr=outlineButton("Asset QR");qr.setOnClickListener(v->showAssetQr(a));actions.addView(qr,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(actions);''',
'''        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);if(canPerformFieldWork()){MaterialButton job=button("+ Service job");job.setOnClickListener(v->showJobDialog(0,id));actions.addView(job,new LinearLayout.LayoutParams(0,dp(50),1));actions.addView(spacerH());}MaterialButton qr=outlineButton("Asset QR");qr.setOnClickListener(v->showAssetQr(a));actions.addView(qr,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(actions);''',
'asset service action')

account_anchor = '''    private void showAccountWorkspace(){\n        setHeader("Account & Workspace","Supabase identity, ownership & offline workspace");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);'''
account_new = '''    private void showAccountWorkspace(){\n        setHeader("Account & Workspace","Identity, workspace access & cloud sync");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);\n        if(hasPendingWorkspaceInvite()&&!accountTeam.hasCloudWorkspace()){showPendingInviteOnboarding(b);return;}'''
s = replace_once(s, account_anchor, account_new, 'account pending invite routing')

local_block = '''        b.addView(section("Local workspace"));EditText workspace=input("Workspace / company name",accountTeam.workspaceName().isEmpty()?prefs.getString("company_name","Fidalix Limited"):accountTeam.workspaceName());EditText person=input("Your name",accountTeam.accountName().isEmpty()?prefs.getString("technician_name",""):accountTeam.accountName());EditText localEmail=input("Account email",accountTeam.accountEmail().isEmpty()?prefs.getString("company_email",""):accountTeam.accountEmail());b.addView(workspace);b.addView(person);b.addView(localEmail);\n        MaterialButton save=outlineButton(accountTeam.hasWorkspace()?"Save local profile":"Create local workspace");save.setOnClickListener(v->{if(val(workspace).isEmpty()){workspace.setError("Workspace name required");return;}if(val(person).isEmpty()){person.setError("Your name required");return;}if(!val(localEmail).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(localEmail)).matches()){localEmail.setError("Enter a valid email");return;}accountTeam.saveOwnerWorkspace(val(workspace),val(person),val(localEmail));toast("Local workspace profile saved");showAccountWorkspace();});b.addView(save);'''
local_new = '''        EditText workspace=input("Workspace / company name",accountTeam.workspaceName().isEmpty()?prefs.getString("company_name","Fidalix Limited"):accountTeam.workspaceName());EditText person=input("Your name",accountTeam.accountName().isEmpty()?prefs.getString("technician_name",""):accountTeam.accountName());EditText localEmail=input("Account email",accountTeam.accountEmail().isEmpty()?prefs.getString("company_email",""):accountTeam.accountEmail());\n        if(canManageWorkspaceSettings()){b.addView(section("Local workspace"));b.addView(workspace);b.addView(person);b.addView(localEmail);MaterialButton save=outlineButton(accountTeam.hasWorkspace()?"Save local profile":"Create local workspace");save.setOnClickListener(v->{if(val(workspace).isEmpty()){workspace.setError("Workspace name required");return;}if(val(person).isEmpty()){person.setError("Your name required");return;}if(!val(localEmail).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(localEmail)).matches()){localEmail.setError("Enter a valid email");return;}accountTeam.saveOwnerWorkspace(val(workspace),val(person),val(localEmail));toast("Local workspace profile saved");showAccountWorkspace();});b.addView(save);}else{b.addView(section("Your workspace access"));b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Name",accountTeam.accountName()));b.addView(info("Email",accountTeam.accountEmail()));b.addView(info("Role",accountTeam.accountRole()));b.addView(paragraph("Workspace/company identity is controlled by Owner/Admin. Your account can still sync and work with the service jobs allowed by your role."));}'''
s = replace_once(s, local_block, local_new, 'account local profile manager control')

s = replace_once(s,
'''            b.addView(section("Create or join workspace"));MaterialButton create=button("Create cloud workspace");create.setOnClickListener(v->{String name=val(workspace);if(name.isEmpty()){workspace.setError("Workspace name required");return;}runCloud("Creating cloud workspace…",()->cloudSync.createWorkspace(name),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Cloud workspace created");showAccountWorkspace();});});b.addView(create);\n            EditText invite=input("Invitation code","");''',
'''            b.addView(section("Create or join workspace"));if(canManageWorkspaceSettings()){MaterialButton create=button("Create cloud workspace");create.setOnClickListener(v->{String name=val(workspace);if(name.isEmpty()){workspace.setError("Workspace name required");return;}runCloud("Creating cloud workspace…",()->cloudSync.createWorkspace(name),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Cloud workspace created");showAccountWorkspace();});});b.addView(create);}\n            EditText invite=input("Invitation code","");''',
'workspace create role')

helper_anchor = '''    private void showAccountWorkspace(){'''
invite_helpers = '''    private void showPendingInviteOnboarding(LinearLayout b){\n        String token=pendingWorkspaceInviteToken(),invitedEmail=pendingWorkspaceInviteEmail();\n        b.addView(section("Workspace invitation"));b.addView(paragraph("Invitation loaded from your email. No code entry is required. Create an account or sign in with the invited email and Fida Field will join the workspace automatically."));\n        if(!cloudSync.backendConfigured()){b.addView(empty("This build does not contain the Supabase cloud configuration."));return;}\n        if(cloudSync.signedIn()){\n            String signed=cloudSync.accountEmail();b.addView(info("Signed in as",signed));\n            if(!invitedEmail.isEmpty()&&!signed.equalsIgnoreCase(invitedEmail)){b.addView(empty("This invitation is for "+invitedEmail+", but this device is signed in as "+signed+"."));MaterialButton out=outlineButton("Sign out and use invited email");out.setOnClickListener(v->runCloud("Signing out…",()->{cloudSync.signOut();return null;},obj->{accountTeam.clearCloudBinding();showAccountWorkspace();}));b.addView(out);return;}\n            MaterialButton join=button("Join workspace now");join.setOnClickListener(v->acceptPendingInviteNow(accountTeam.accountName()));b.addView(join);return;\n        }\n        EditText name=input("Your name",accountTeam.accountName().isEmpty()?prefs.getString("technician_name",""):accountTeam.accountName());EditText email=input("Invited email",invitedEmail);if(!invitedEmail.isEmpty())email.setEnabled(false);EditText password=input("Password","");password.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(name);b.addView(email);b.addView(password);\n        MaterialButton create=button("Create account & join");create.setOnClickListener(v->{String n=val(name),e=val(email),pw=val(password);if(n.isEmpty()){name.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(pw.length()<6){password.setError("Use at least 6 characters");return;}runCloud("Creating account…",()->cloudSync.signUp(n,e,pw),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(ar.signedIn)acceptPendingInviteNow(n);else new MaterialAlertDialogBuilder(this).setTitle("One confirmation step").setMessage("We created your account. Confirm the email from Fida Field/Supabase once, then return here and tap Sign in & join. The workspace invitation is already saved — you will not need to enter the code.").setPositiveButton("OK",(d,w)->showAccountWorkspace()).show();});});b.addView(create);\n        MaterialButton signIn=outlineButton("Already registered? Sign in & join");signIn.setOnClickListener(v->{String n=val(name),e=val(email),pw=val(password);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(pw.isEmpty()){password.setError("Password required");return;}runCloud("Signing in…",()->cloudSync.signIn(e,pw),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);acceptPendingInviteNow(n);});});b.addView(signIn);\n        b.addView(paragraph("Fallback: if the email button did not open Fida Field, you can still sign in normally and use the invitation code shown in the email."));\n    }\n\n    private void acceptPendingInviteNow(String displayName){\n        String token=pendingWorkspaceInviteToken();if(token.isEmpty()){showAccountWorkspace();return;}\n        runCloud("Joining workspace…",()->cloudSync.acceptInvite(token),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudAccount(cloudSync.userId(),displayName,cloudSync.accountEmail());accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);clearPendingWorkspaceInvite();runCloud("Loading your workspace…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Joined "+wm.name+" as "+wm.role);showDashboard();});});\n    }\n\n    private void showAccountWorkspace(){'''
s = replace_once(s, helper_anchor, invite_helpers, 'invite onboarding helpers')

old_msg = '''new MaterialAlertDialogBuilder(this).setTitle(cloudSync.lastInviteEmailSent()?"Invitation sent":"Invitation created").setMessage("Share this code with "+e+". After they join, Fida Field will automatically link the account to a matching field profile when the email is the same.\\n\\n"+token)'''
new_msg = '''new MaterialAlertDialogBuilder(this).setTitle(cloudSync.lastInviteEmailSent()?"Invitation sent":"Invitation created").setMessage((cloudSync.lastInviteEmailSent()?"Email sent to "+e+". On Android, the recipient can tap ‘Open Fida Field & join’ and the invitation will load automatically. The code below is only a fallback.":"Email delivery was not confirmed. Share this fallback invitation code with "+e+".")+"\\n\\n"+token)'''
s = replace_once(s, old_msg, new_msg, 'invite success message')

s = s.replace('Fida Field 0.9.16 Test', 'Fida Field 0.9.17 Test')
p.write_text(s)

p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
s = p.read_text()
anchor = '''    public List<Row> pendingBusinessSyncRows(){return rows("SELECT q.*,m.remote_uuid,m.server_version,m.last_synced_at FROM sync_queue q LEFT JOIN sync_metadata m ON m.entity_type=q.entity_type AND m.entity_id=q.entity_id WHERE q.entity_type IN ('customer','site','asset','technician','job') ORDER BY q.changed_at,q.id",null);}\n'''
addition = anchor + '''    public void discardManagerOnlyPendingChanges(){getWritableDatabase().delete("sync_queue","entity_type IN ('customer','site','asset','technician')",null);getWritableDatabase().delete("sync_conflicts","entity_type IN ('customer','site','asset','technician')",null);}\n'''
s = replace_once(s, anchor, addition, 'discard restricted sync queue')
p.write_text(s)

p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s = p.read_text()
old = '''            int pushed=0,pulled=0,deferred=0;String[] pushOrder={"customer","site","asset","technician","job"};String[] deleteOrder={"job","asset","site","customer","technician"};List<AppDatabase.Row> pending=db.pendingBusinessSyncRows();java.util.ArrayList<Long> finalizeCompleted=new java.util.ArrayList<>();java.util.HashSet<String> visibleJobIds=new java.util.HashSet<>();'''
new = '''            int pushed=0,pulled=0,deferred=0;if(!canManage)db.discardManagerOnlyPendingChanges();String[] pushOrder=canManage?new String[]{"customer","site","asset","technician","job"}:new String[]{"job"};String[] deleteOrder=canManage?new String[]{"job","asset","site","customer","technician"}:new String[]{"job"};List<AppDatabase.Row> pending=db.pendingBusinessSyncRows();java.util.ArrayList<Long> finalizeCompleted=new java.util.ArrayList<>();java.util.HashSet<String> visibleJobIds=new java.util.HashSet<>();'''
s = replace_once(s, old, new, 'non-manager sync push scope')
p.write_text(s)

p = Path('fida-field/app/build.gradle')
s = p.read_text()
if 'versionCode 19' not in s or "versionName '0.9.16-test'" not in s:
    raise AssertionError('0.9.16 version anchors not found')
s = s.replace('versionCode 19','versionCode 20',1).replace("versionName '0.9.16-test'","versionName '0.9.17-test'",1)
p.write_text(s)
