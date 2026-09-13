from pathlib import Path

GRADLE = Path('fida-field/app/build.gradle')
MAIN = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:240]!r}')
    path.write_text(text.replace(old, new, 1))


replace_once(
    GRADLE,
    "versionCode 45\n        versionName '0.9.42-test'",
    "versionCode 46\n        versionName '0.9.43-test'",
)

# 1) Make Home role-aware and task-focused for technicians while preserving the richer
# management dashboard for Owner/Admin users. Add a visible sync-status shortcut for
# every cloud workspace user.
replace_once(
    MAIN,
    '''        long openJobs=db.visibleOpenJobCount(currentJobUserUuid(),canSeeAllJobs());long due30=db.dueAssets(30).size();LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(dashboardStat("Open jobs",openJobs,v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));stats.addView(spacerH());stats.addView(dashboardStat("Due ≤30d",due30,v->showMaintenance(30)),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats);\n        MaterialCardView planCard=rowCard(entitlements.planName(),entitlements.usageSummary(),entitlements.isPro()?"PRO":entitlements.freeReportsRemaining()+" left");planCard.setOnClickListener(v->showPlan());b.addView(planCard);\n        long customerCount=db.count("customers",null,null),assetCount=db.count("assets",null,null);LinearLayout stats2=new LinearLayout(this);stats2.setOrientation(LinearLayout.HORIZONTAL);stats2.setPadding(0,dp(8),0,0);stats2.addView(dashboardStat("Customers",customerCount,v->showCustomers()),new LinearLayout.LayoutParams(0,dp(102),1));stats2.addView(spacerH());stats2.addView(dashboardStat("Assets",assetCount,v->showAssets()),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats2);\n''',
    '''        long openJobs=db.visibleOpenJobCount(currentJobUserUuid(),canSeeAllJobs());\n        if(canSeeAllJobs()){\n            long due30=db.dueAssets(30).size();LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(dashboardStat("Open jobs",openJobs,v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));stats.addView(spacerH());stats.addView(dashboardStat("Due ≤30d",due30,v->showMaintenance(30)),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats);\n            MaterialCardView planCard=rowCard(entitlements.planName(),entitlements.usageSummary(),entitlements.isPro()?"PRO":entitlements.freeReportsRemaining()+" left");planCard.setOnClickListener(v->showPlan());b.addView(planCard);\n            long customerCount=db.count("customers",null,null),assetCount=db.count("assets",null,null);LinearLayout stats2=new LinearLayout(this);stats2.setOrientation(LinearLayout.HORIZONTAL);stats2.setPadding(0,dp(8),0,0);stats2.addView(dashboardStat("Customers",customerCount,v->showCustomers()),new LinearLayout.LayoutParams(0,dp(102),1));stats2.addView(spacerH());stats2.addView(dashboardStat("Assets",assetCount,v->showAssets()),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats2);\n        }else{\n            List<AppDatabase.Row> inProgress=db.jobsFilteredScoped("","In Progress","All","All","","",currentJobUserUuid(),false);LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(dashboardStat("My open jobs",openJobs,v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));stats.addView(spacerH());stats.addView(dashboardStat("In progress",inProgress.size(),v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats);\n            if(canPerformFieldWork()&&!inProgress.isEmpty()){AppDatabase.Row focus=null;for(AppDatabase.Row candidate:inProgress)if(db.jobServiceRunning(candidate.id())){focus=candidate;break;}if(focus==null)focus=inProgress.get(0);final AppDatabase.Row focusJob=focus;String state=db.jobServiceRunning(focusJob.id())?"Running":"Paused";MaterialCardView continueCard=rowCard("Continue current job",focusJob.s("report_no")+" · "+focusJob.s("title"),state);continueCard.setOnClickListener(v->showJobDetail(focusJob.id()));b.addView(continueCard);}\n        }\n        if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){long pending=cloudSync.pendingChanges(),conflicts=cloudSync.conflictCount();String badge=conflicts>0?conflicts+" conflict"+(conflicts==1?"":"s"):pending>0?pending+" pending":"Up to date";String syncMeta="Last sync: "+cloudSync.lastSync()+(pending>0?" · "+pending+" pending":"");MaterialCardView syncCard=rowCard("Cloud sync",syncMeta,badge);syncCard.setOnClickListener(v->showCloudSync());b.addView(syncCard);}\n'''
)

replace_once(
    MAIN,
    '''        List<AppDatabase.Row> due=db.dueAssets(30);b.addView(section("Maintenance attention"));if(due.isEmpty())b.addView(empty("Nothing due in the next 30 days."));else for(int i=0;i<Math.min(4,due.size());i++){AppDatabase.Row r=due.get(i);MaterialCardView c=rowCard(r.s("name"),r.s("customer_name")+" • Due "+r.s("next_service"),r.s("tag"));c.setOnClickListener(v->showAssetDetail(r.id()));b.addView(c);}\n''',
    '''        if(canSeeAllJobs()){List<AppDatabase.Row> due=db.dueAssets(30);b.addView(section("Maintenance attention"));if(due.isEmpty())b.addView(empty("Nothing due in the next 30 days."));else for(int i=0;i<Math.min(4,due.size());i++){AppDatabase.Row r=due.get(i);MaterialCardView c=rowCard(r.s("name"),r.s("customer_name")+" • Due "+r.s("next_service"),r.s("tag"));c.setOnClickListener(v->showAssetDetail(r.id()));b.addView(c);}}\n'''
)

# 2) Jobs screen: give users a one-tap way to recover from complex filter combinations.
replace_once(
    MAIN,
    '''        b.addView(label("Technician"));Spinner technician=spinner(canSeeAllJobs()?technicianFilterValues():new String[]{"My assigned jobs"});b.addView(technician);\n        LinearLayout list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);b.addView(list);\n''',
    '''        b.addView(label("Technician"));Spinner technician=spinner(canSeeAllJobs()?technicianFilterValues():new String[]{"My assigned jobs"});b.addView(technician);MaterialButton clearFilters=outlineButton("Clear filters");b.addView(clearFilters);\n        LinearLayout list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);b.addView(list);\n'''
)

replace_once(
    MAIN,
    '''        search.addTextChangedListener(watcher(reload));AdapterView.OnItemSelectedListener l=new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long id){reload.run();}public void onNothingSelected(AdapterView<?>p){}};status.setOnItemSelectedListener(l);priority.setOnItemSelectedListener(l);date.setOnItemSelectedListener(l);technician.setOnItemSelectedListener(l);reload.run();\n''',
    '''        search.addTextChangedListener(watcher(reload));AdapterView.OnItemSelectedListener l=new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long id){reload.run();}public void onNothingSelected(AdapterView<?>p){}};status.setOnItemSelectedListener(l);priority.setOnItemSelectedListener(l);date.setOnItemSelectedListener(l);technician.setOnItemSelectedListener(l);clearFilters.setOnClickListener(v->{search.setText("");status.setSelection(0);priority.setSelection(0);date.setSelection(0);if(canSeeAllJobs())technician.setSelection(0);reload.run();});reload.run();\n'''
)

# 3) Job form: filter assets by the selected customer/site and keep the dependent
# pickers synchronized. This avoids showing unrelated equipment in a long global list.
replace_once(
    MAIN,
    '''Spinner site=choiceSpinner(siteChoices(true,customerId));long siteId=id>0?parse(r.s("site_id")):parse(ar.s("site_id"));setChoice(site,siteId);customer.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long rowId){long keep=selectedChoiceId(site);Choice c=(Choice)customer.getSelectedItem();replaceChoices(site,siteChoices(true,c==null?0:c.id),keep);}public void onNothingSelected(AdapterView<?>p){}});Spinner asset=choiceSpinner(assetChoices(true));long assetId=id>0?parse(r.s("asset_id")):preferredAsset;setChoice(asset,assetId);''',
    '''Spinner site=choiceSpinner(siteChoices(true,customerId));long siteId=id>0?parse(r.s("site_id")):parse(ar.s("site_id"));setChoice(site,siteId);Spinner asset=choiceSpinner(assetChoices(true,customerId,siteId));long assetId=id>0?parse(r.s("asset_id")):preferredAsset;setChoice(asset,assetId);customer.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long rowId){long keepSite=selectedChoiceId(site),keepAsset=selectedChoiceId(asset);Choice c=(Choice)customer.getSelectedItem();long cid=c==null?0:c.id;replaceChoices(site,siteChoices(true,cid),keepSite);replaceChoices(asset,assetChoices(true,cid,selectedChoiceId(site)),keepAsset);}public void onNothingSelected(AdapterView<?>p){}});site.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long rowId){long keepAsset=selectedChoiceId(asset);replaceChoices(asset,assetChoices(true,selectedChoiceId(customer),selectedChoiceId(site)),keepAsset);}public void onNothingSelected(AdapterView<?>p){}});'''
)

# 4) Break the long service-job form into meaningful sections and explicitly label dates.
replace_once(
    MAIN,
    '''form.addView(label("Customer"));form.addView(customer);form.addView(label("Site"));form.addView(site);form.addView(label("Asset"));form.addView(asset);form.addView(jobTitle);form.addView(problem);form.addView(diagnosis);form.addView(work);form.addView(parts);MaterialButton checklist=outlineButton("Service checklist");checklist.setOnClickListener(v->showServiceChecklist(work));form.addView(checklist);MaterialButton aiAssist=outlineButton("AI assist report");aiAssist.setOnClickListener(v->showAiReportAssistant(jobTitle,problem,diagnosis,work,parts));form.addView(aiAssist);form.addView(label("Technician"));form.addView(tech);form.addView(label("Priority"));form.addView(priority);form.addView(label("Status"));form.addView(status);form.addView(date);form.addView(next);''',
    '''form.addView(paragraph("Fields marked * are required."));form.addView(section("Location & equipment"));form.addView(label("Customer"));form.addView(customer);form.addView(label("Site"));form.addView(site);form.addView(label("Asset"));form.addView(asset);form.addView(section("Service details"));form.addView(jobTitle);form.addView(problem);form.addView(diagnosis);form.addView(work);form.addView(parts);MaterialButton checklist=outlineButton("Service checklist");checklist.setOnClickListener(v->showServiceChecklist(work));form.addView(checklist);MaterialButton aiAssist=outlineButton("AI assist report");aiAssist.setOnClickListener(v->showAiReportAssistant(jobTitle,problem,diagnosis,work,parts));form.addView(aiAssist);form.addView(section("Assignment & schedule"));form.addView(label("Technician"));form.addView(tech);form.addView(label("Priority"));form.addView(priority);form.addView(label("Status"));form.addView(status);form.addView(label("Service date"));form.addView(date);form.addView(label("Next recommended service"));form.addView(next);'''
)

replace_once(
    MAIN,
    '''    private List<Choice> assetChoices(boolean empty){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— None —"));for(AppDatabase.Row r:db.assets(0,0))out.add(new Choice(r.id(),r.s("tag")+" / "+r.s("name")));return out;}\n''',
    '''    private List<Choice> assetChoices(boolean empty){return assetChoices(empty,0,0);}\n    private List<Choice> assetChoices(boolean empty,long customerId,long siteId){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— None —"));for(AppDatabase.Row r:db.assets(customerId,siteId))out.add(new Choice(r.id(),r.s("tag")+" / "+r.s("name")));return out;}\n'''
)

# 5) Completing a job locks it for technicians; require an explicit confirmation so
# an accidental tap does not immediately end the service workflow.
replace_once(
    MAIN,
    '''MaterialButton complete=outlineButton("Mark job completed");complete.setOnClickListener(v->{long aid=parse(j.s("asset_id"));String ns=j.s("next_service");if(aid>0&&ns.isEmpty())ns=db.suggestNextService(aid,j.s("job_date"));db.completeJobService(id);if(aid>0)db.completeMaintenanceIfNeeded(aid,id,j.s("work_done"),ns);toast(ns.isEmpty()?"Job completed":"Job completed • next service "+ns);showJobDetail(id);});b.addView(complete);''',
    '''MaterialButton complete=outlineButton("Mark job completed");complete.setOnClickListener(v->new MaterialAlertDialogBuilder(this).setTitle("Complete this job?").setMessage("This stops the active service timer and marks the job Completed. Technician accounts cannot edit a completed job unless an Owner or Admin reopens/corrects it.").setNegativeButton("Not yet",null).setPositiveButton("Complete job",(d,w)->{long aid=parse(j.s("asset_id"));String ns=j.s("next_service");if(aid>0&&ns.isEmpty())ns=db.suggestNextService(aid,j.s("job_date"));db.completeJobService(id);if(aid>0)db.completeMaintenanceIfNeeded(aid,id,j.s("work_done"),ns);toast(ns.isEmpty()?"Job completed":"Job completed • next service "+ns);showJobDetail(id);}).show());b.addView(complete);'''
)

print('Fida Field 0.9.43 field UX polish applied')
