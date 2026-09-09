from pathlib import Path

main_path = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
supa_path = Path('fida-field/app/src/main/java/com/fidalix/fidafield/SupabaseClientLite.java')
text = main_path.read_text()

def rep(old, new, count=1):
    global text
    if old not in text:
        raise SystemExit('missing MainActivity marker: ' + old[:100])
    text = text.replace(old, new, count)

rep('    private AccountTeamManager accountTeam;\n', '    private AccountTeamManager accountTeam;\n    private BillingManager billingManager;\n')
rep('        accountTeam=new AccountTeamManager(prefs,db);\n        migrateDefaultTechnician();',
    '        accountTeam=new AccountTeamManager(prefs,db);\n        billingManager=new BillingManager(this,prefs,()->refreshEntitlementsAndBranding());\n        billingManager.start();\n        migrateDefaultTechnician();')
rep('        showDashboard();\n    }\n\n    private void applyThemeMode',
    '        showDashboard();\n    }\n\n    @Override protected void onResume(){super.onResume();if(billingManager!=null)billingManager.refreshPurchases();}\n    @Override protected void onDestroy(){if(billingManager!=null)billingManager.stop();super.onDestroy();}\n\n    private void applyThemeMode')

rep('        b.addView(menuCard("Technicians","Team members and job assignment",v->showTechnicians()));',
    '        b.addView(menuCard("People & Team",db.technicians().size()+" field technicians • "+accountTeam.teamSummary(),v->showPeopleTeam()));')
rep('        b.addView(menuCard("Team members",accountTeam.teamSummary(),v->showTeam()));\n', '')
text = text.replace('Fida Field 0.9.11 Test', 'Fida Field 0.9.12 Test')
text = text.replace('toast("Technician saved");showTechnicians();', 'toast("Technician saved");showPeopleTeam();')
text = text.replace('showTeam();', 'showPeopleTeam();')

people_method = r'''    private void showPeopleTeam(){
        setHeader("People & Team","Job assignment & workspace access");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        b.addView(paragraph("Field technicians are the people available for job assignment. Workspace members control who can sign in and access this cloud workspace. A person can be both, but both responsibilities are now managed from this single screen."));

        b.addView(section("Field technicians"));MaterialButton add=button("+ Add field technician");add.setOnClickListener(v->showTechnicianDialog(0));b.addView(add);
        List<AppDatabase.Row> techs=db.technicians();if(techs.isEmpty())b.addView(empty("Add technicians to assign service work consistently."));
        for(AppDatabase.Row r:techs){String meta=(r.s("role").isEmpty()?"Technician":r.s("role"))+(r.s("email").isEmpty()?"":" • "+r.s("email"))+(r.s("phone").isEmpty()?"":" • "+r.s("phone"));MaterialCardView c=rowCard(r.s("name"),meta,r.i("active")==1?"Job active":"Job inactive");c.setOnClickListener(v->showTechnicianDialog(r.id()));b.addView(c);}

        b.addView(section("Workspace access"));
        if(!accountTeam.hasWorkspace()){b.addView(empty("Create your workspace before adding cloud members."));MaterialButton setup=outlineButton("Set up workspace");setup.setOnClickListener(v->showAccountWorkspace());b.addView(setup);return;}
        boolean cloud=accountTeam.hasCloudWorkspace()&&cloudSync.signedIn();b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Your access role",accountTeam.accountRole()));b.addView(info("Mode",cloud?"Cloud workspace · Supabase":"Local workspace"));
        if(cloud){MaterialButton refresh=outlineButton("Refresh workspace members");refresh.setOnClickListener(v->runCloud("Refreshing team…",()->{cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{toast("Team refreshed");showPeopleTeam();}));b.addView(refresh);}
        if(accountTeam.canManageTeam()){MaterialButton invite=button("+ Invite workspace member");invite.setOnClickListener(v->showInviteDialog());b.addView(invite);}else b.addView(paragraph("Only workspace Owners and Admins can manage access roles and invitations."));
        List<AppDatabase.Row> members=db.workspaceMembers(accountTeam.workspaceId());if(members.isEmpty())b.addView(empty(cloud?"Refresh to download workspace members.":"No workspace members yet."));
        for(AppDatabase.Row r:members){String meta=(r.s("email").isEmpty()?"No email":r.s("email"))+" • "+r.s("status");MaterialCardView c=rowCard(r.s("name"),meta,"Cloud: "+r.s("role"));if(accountTeam.canManageTeam()&&!"Owner".equals(r.s("role")))c.setOnClickListener(v->showMemberDialog(r.id()));b.addView(c);}

        List<AppDatabase.Row> invites=db.workspaceInvites(accountTeam.workspaceId());b.addView(section("Pending invitations"));if(invites.isEmpty())b.addView(empty("No pending invitations."));
        for(AppDatabase.Row r:invites){MaterialCardView c=rowCard(r.s("email"),r.s("role"),r.s("status"));if("Pending".equals(r.s("status")))c.setOnClickListener(v->{String code=r.s("token");MaterialAlertDialogBuilder d=new MaterialAlertDialogBuilder(this).setTitle("Pending invitation").setMessage(r.s("email")+" · "+r.s("role")+(code.isEmpty()?"":"\n\nInvitation code:\n"+code)+(r.s("expires_at").isEmpty()?"":"\nExpires: "+r.s("expires_at"))).setNegativeButton("Close",null);if(!code.isEmpty())d.setNeutralButton("Copy code",(x,w)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",code));toast("Invitation code copied");});if(accountTeam.canManageTeam())d.setPositiveButton("Cancel invitation",(x,w)->{if(cloud)runCloud("Cancelling invitation…",()->{cloudSync.cancelInvite(r.s("invite_uuid"));cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return null;},z->{toast("Invitation cancelled");showPeopleTeam();});else{db.cancelWorkspaceInvite(r.id());showPeopleTeam();}});d.show();});b.addView(c);}
    }

'''
marker = '    private void showTechnicians(){'
if marker not in text:
    raise SystemExit('missing technician method marker')
text = text.replace(marker, people_method + marker, 1)

start = text.index('    private void showPlan(){')
end = text.index('    private void showBranding(){', start)
plan = r'''    private void showPlan(){
        setHeader("Plan & Subscription",BuildConfig.OPEN_EDITION?"Fidalix internal edition":"Google Play subscription");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        refreshEntitlementsAndBranding();
        b.addView(section("Current plan"));b.addView(info("Plan",entitlements.planName()));b.addView(info("Entitlement",entitlements.entitlementSource()));b.addView(info("Monthly usage",entitlements.usageSummary()));
        if(BuildConfig.OPEN_EDITION){
            b.addView(section("Fidalix Open"));b.addView(paragraph("This internal company edition does not use Google Play Billing. Pro capabilities are permanently enabled by the signed build itself, while cloud accounts, workspace security and Supabase synchronization continue to work normally."));b.addView(info("Billing","Not required"));b.addView(info("Distribution","Direct/internal APK"));return;
        }
        b.addView(info("Free allowance",EntitlementManager.FREE_MONTHLY_REPORT_LIMIT+" new service reports / month"));
        b.addView(section("Google Play Pro"));b.addView(paragraph("Pro unlocks unlimited service reports, CSV exports and custom company branding. Purchases are not trusted locally: Fida Field sends the Google Play purchase token to the authenticated Supabase backend, which verifies it with Google Play before Pro is enabled."));
        b.addView(info("Billing status",billingManager==null?"Initializing":billingManager.lastResult()));b.addView(info("Subscription state",billingManager==null||billingManager.subscriptionState().isEmpty()?"Not verified":billingManager.subscriptionState()));b.addView(info("Expires",billingManager==null||billingManager.expiry().isEmpty()?"—":billingManager.expiry()));
        if(!cloudSync.signedIn()){b.addView(paragraph("Sign in to your Fida Field account before buying or restoring Pro so the verified entitlement can be securely attached to your account."));MaterialButton account=outlineButton("Open Account & Workspace");account.setOnClickListener(v->showAccountWorkspace());b.addView(account);}
        String monthly=billingManager==null?"Not loaded":billingManager.displayPrice(EntitlementManager.PRODUCT_PRO_MONTHLY);String annual=billingManager==null?"Not loaded":billingManager.displayPrice(EntitlementManager.PRODUCT_PRO_ANNUAL);
        MaterialButton buyMonthly=button("Monthly Pro · "+monthly);buyMonthly.setEnabled(cloudSync.signedIn());buyMonthly.setOnClickListener(v->{if(billingManager!=null)billingManager.purchase(this,EntitlementManager.PRODUCT_PRO_MONTHLY);});b.addView(buyMonthly);
        MaterialButton buyAnnual=button("Annual Pro · "+annual);buyAnnual.setEnabled(cloudSync.signedIn());buyAnnual.setOnClickListener(v->{if(billingManager!=null)billingManager.purchase(this,EntitlementManager.PRODUCT_PRO_ANNUAL);});b.addView(buyAnnual);
        MaterialButton restore=outlineButton("Restore / refresh purchases");restore.setOnClickListener(v->{if(billingManager!=null){billingManager.restore();toast("Checking Google Play and server entitlement…");}});b.addView(restore);
        b.addView(paragraph("If the subscription products are not yet active for this Play testing track, the purchase buttons will show Not available until the products/base plans are published in Google Play Console."));
    }

'''
text = text[:start] + plan + text[end:]
main_path.write_text(text)

supa = supa_path.read_text()
if 'invokeFunction(String function' not in supa:
    marker = '    /** Standard Supabase Storage upload. x-upsert makes retries idempotent. */'
    if marker not in supa:
        raise SystemExit('missing Supabase function insertion marker')
    method = '''    public Object invokeFunction(String function,JSONObject body)throws Exception{\n        String name=function==null?"":function.trim();if(name.isEmpty())throw new Exception("Missing Edge Function name");\n        return request("POST",BuildConfig.SUPABASE_URL+"/functions/v1/"+enc(name),body==null?new JSONObject():body,true,null,null);\n    }\n\n'''
    supa = supa.replace(marker, method + marker, 1)
supa_path.write_text(supa)
