from pathlib import Path

GRADLE=Path('fida-field/app/build.gradle')
MANIFEST=Path('fida-field/app/src/main/AndroidManifest.xml')
DB=Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
MAIN=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')


def replace_once(path:Path,old:str,new:str):
    text=path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:240]!r}')
    path.write_text(text.replace(old,new,1))


def replace_between(path:Path,start_marker:str,end_marker:str,new_block:str):
    text=path.read_text()
    start=text.find(start_marker)
    if start<0: raise SystemExit(f'Start marker not found in {path}: {start_marker}')
    end=text.find(end_marker,start)
    if end<0: raise SystemExit(f'End marker not found in {path}: {end_marker}')
    path.write_text(text[:start]+new_block+text[end:])

replace_once(GRADLE,"versionCode 50\n        versionName '0.9.47-test'","versionCode 51\n        versionName '0.9.48-test'")
replace_once(MANIFEST,'    <uses-permission android:name="android.permission.INTERNET" />\n','    <uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n')

replace_once(
    DB,
    '    public void reassignJob(long jobId,long technicianId,String actor){Row job=getJob(jobId),tech=getTechnician(technicianId);if(job.id()==0||tech.id()==0)return;long old=job.i("technician_id");if(old==technicianId)return;ContentValues v=new ContentValues();v.put("technician_id",technicianId);v.put("technician",tech.s("name"));v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});recordLocalAssignment(jobId,old,technicianId,actor);queueSync("job",jobId,"upsert");}\n',
    '''    public void updateJobFieldNotes(long jobId,String diagnosis,String workDone,String parts){if(jobId<=0)return;ContentValues v=new ContentValues();v.put("diagnosis",diagnosis==null?"":diagnosis);v.put("work_done",workDone==null?"":workDone);v.put("parts",parts==null?"":parts);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");}\n    public long jobSyncPendingCount(long jobId){if(jobId<=0)return 0;return count("sync_queue","(entity_type='job' AND entity_id=?) OR (entity_type='job_photo' AND entity_id IN (SELECT id FROM job_photos WHERE job_id=?)) OR (entity_type='job_signature' AND entity_id=?)",new String[]{String.valueOf(jobId),String.valueOf(jobId),String.valueOf(jobId)});}\n    public void reassignJob(long jobId,long technicianId,String actor){Row job=getJob(jobId),tech=getTechnician(technicianId);if(job.id()==0||tech.id()==0)return;long old=job.i("technician_id");if(old==technicianId)return;ContentValues v=new ContentValues();v.put("technician_id",technicianId);v.put("technician",tech.s("name"));v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});recordLocalAssignment(jobId,old,technicianId,actor);queueSync("job",jobId,"upsert");}\n'''
)

helpers=r'''    private boolean networkAvailable(){
        try{android.net.ConnectivityManager cm=(android.net.ConnectivityManager)getSystemService(android.content.Context.CONNECTIVITY_SERVICE);if(cm==null)return false;android.net.Network n=cm.getActiveNetwork();if(n==null)return false;android.net.NetworkCapabilities c=cm.getNetworkCapabilities(n);return c!=null&&c.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET);}catch(Exception e){return false;}
    }

    private String jobSyncState(long jobId){
        if(accountTeam==null||!accountTeam.hasCloudWorkspace()||cloudSync==null||!cloudSync.signedIn())return "Saved on this device";long pending=db.jobSyncPendingCount(jobId);if(!networkAvailable())return pending>0?"Offline · "+pending+" change"+(pending==1?"":"s")+" saved locally":"Offline · local copy available";return pending>0?pending+" change"+(pending==1?"":"s")+" pending sync":"Synced with workspace";
    }

    private void startJobAndOpen(long jobId){
        AppDatabase.Row j=db.getJob(jobId);if(j.id()==0){toast("Job not found");return;}if(!canPerformFieldWork()||!canSeeJob(j)){toast("This job is not available for field work");return;}if("Completed".equalsIgnoreCase(j.s("status"))||"Cancelled".equalsIgnoreCase(j.s("status"))){showJobDetail(jobId);return;}boolean already=db.jobServiceRunning(jobId);if(!already)db.startJobService(jobId);toast(already?"Opening current job":j.l("service_started_at_ms")>0?"Service resumed":"Service started · saved locally");showJobDetail(jobId);
    }

    private void renderFieldJobFocus(LinearLayout b){
        if(!canPerformFieldWork()||canSeeAllJobs())return;List<AppDatabase.Row> active=db.jobsFilteredScoped("","In Progress","All","All","","",currentJobUserUuid(),false);if(!active.isEmpty()){AppDatabase.Row focus=null;for(AppDatabase.Row r:active)if(db.jobServiceRunning(r.id())){focus=r;break;}if(focus==null)focus=active.get(0);final AppDatabase.Row job=focus;boolean running=db.jobServiceRunning(job.id());String state=running?"Running":"Paused";MaterialCardView card=rowCard("Current field job",job.s("report_no")+" · "+job.s("title")+"\n"+(job.s("customer_name").isEmpty()?"":job.s("customer_name")),state+" · "+serviceDuration(job));card.setOnClickListener(v->showJobDetail(job.id()));b.addView(card);MaterialButton go=button(running?"Continue current job":"Resume service");go.setOnClickListener(v->startJobAndOpen(job.id()));b.addView(go);b.addView(paragraph(jobSyncState(job.id())));return;}List<AppDatabase.Row> open=db.jobsFilteredScoped("","Open","All","All","","",currentJobUserUuid(),false);if(!open.isEmpty()){final AppDatabase.Row next=open.get(0);MaterialCardView card=rowCard("Next assigned job",next.s("report_no")+" · "+next.s("title")+"\n"+(next.s("customer_name").isEmpty()?"":next.s("customer_name")),"Ready");card.setOnClickListener(v->showJobDetail(next.id()));b.addView(card);MaterialButton start=button("Start service");start.setOnClickListener(v->startJobAndOpen(next.id()));b.addView(start);}
    }

'''
replace_once(MAIN,'    private void showDashboard(){\n',helpers+'    private void showDashboard(){\n')

old_dashboard='''        }else{\n            List<AppDatabase.Row> inProgress=db.jobsFilteredScoped("","In Progress","All","All","","",currentJobUserUuid(),false);LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(dashboardStat("My open jobs",openJobs,v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));stats.addView(spacerH());stats.addView(dashboardStat("In progress",inProgress.size(),v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats);\n            if(canPerformFieldWork()&&!inProgress.isEmpty()){AppDatabase.Row focus=null;for(AppDatabase.Row candidate:inProgress)if(db.jobServiceRunning(candidate.id())){focus=candidate;break;}if(focus==null)focus=inProgress.get(0);final AppDatabase.Row focusJob=focus;String state=db.jobServiceRunning(focusJob.id())?"Running":"Paused";MaterialCardView continueCard=rowCard("Continue current job",focusJob.s("report_no")+" · "+focusJob.s("title"),state);continueCard.setOnClickListener(v->showJobDetail(focusJob.id()));b.addView(continueCard);}\n        }\n'''
new_dashboard='''        }else{\n            List<AppDatabase.Row> inProgress=db.jobsFilteredScoped("","In Progress","All","All","","",currentJobUserUuid(),false);LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(dashboardStat("My open jobs",openJobs,v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));stats.addView(spacerH());stats.addView(dashboardStat("In progress",inProgress.size(),v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats);renderFieldJobFocus(b);\n        }\n'''
replace_once(MAIN,old_dashboard,new_dashboard)

replace_once(
    MAIN,
    '        currentMenu=MENU_JOBS;bottom.getMenu().findItem(MENU_JOBS).setChecked(true);setHeader("Jobs","Search, filter & service history");mainTabScreen=true;clear();LinearLayout b=body(page());\n        if(canPerformFieldWork()){',
    '        currentMenu=MENU_JOBS;bottom.getMenu().findItem(MENU_JOBS).setChecked(true);setHeader("Jobs","Search, filter & service history");mainTabScreen=true;clear();LinearLayout b=body(page());\n        if(canPerformFieldWork()&&!canSeeAllJobs())renderFieldJobFocus(b);\n        if(canPerformFieldWork()){'
)

old_render='''    private void renderJobs(LinearLayout list,String q,String status,String priority,String technician,String from,String to){list.removeAllViews();String techFilter=canSeeAllJobs()?technician:"All";List<AppDatabase.Row> rows=db.jobsFilteredScoped(q,status,priority,techFilter,from,to,currentJobUserUuid(),canSeeAllJobs());if(rows.isEmpty()){list.addView(empty("No matching jobs."));return;}TextView count=paragraph(rows.size()+" job(s) found");list.addView(count);for(AppDatabase.Row r:rows){String who=r.s("customer_name").isEmpty()?"No customer":r.s("customer_name");String meta=who+(r.s("site_name").isEmpty()?"":" • "+r.s("site_name"))+" • "+r.s("job_date")+(r.s("technician").isEmpty()?"":" • "+r.s("technician"));String badge=r.s("status")+("Normal".equals(r.s("priority"))||r.s("priority").isEmpty()?"":" · "+r.s("priority"));MaterialCardView c=rowCard(r.s("report_no")+" · "+r.s("title"),meta,badge);c.setOnClickListener(v->showJobDetail(r.id()));list.addView(c);}}\n'''
new_render=r'''    private void renderJobs(LinearLayout list,String q,String status,String priority,String technician,String from,String to){
        list.removeAllViews();String techFilter=canSeeAllJobs()?technician:"All";List<AppDatabase.Row> rows=db.jobsFilteredScoped(q,status,priority,techFilter,from,to,currentJobUserUuid(),canSeeAllJobs());if(rows.isEmpty()){list.addView(empty("No matching jobs."));return;}TextView count=paragraph(rows.size()+" job(s) found");list.addView(count);
        for(AppDatabase.Row r:rows){String who=r.s("customer_name").isEmpty()?"No customer":r.s("customer_name");String meta=who+(r.s("site_name").isEmpty()?"":" • "+r.s("site_name"))+" • "+r.s("job_date")+(r.s("technician").isEmpty()?"":" • "+r.s("technician"));String badge=r.s("status")+("Normal".equals(r.s("priority"))||r.s("priority").isEmpty()?"":" · "+r.s("priority"));MaterialCardView c=rowCard(r.s("report_no")+" · "+r.s("title"),meta,badge);c.setOnClickListener(v->showJobDetail(r.id()));list.addView(c);if(canPerformFieldWork()&&!canSeeAllJobs()&&("Open".equals(r.s("status"))||"In Progress".equals(r.s("status")))){boolean running=db.jobServiceRunning(r.id());MaterialButton field=outlineButton("Open".equals(r.s("status"))?"Start service":running?"Continue job":"Resume service");field.setOnClickListener(v->startJobAndOpen(r.id()));list.addView(field);}}
    }
'''
replace_once(MAIN,old_render,new_render)

field_helpers=r'''    private void showFieldNotesDialog(long jobId){
        AppDatabase.Row j=db.getJob(jobId);if(j.id()==0)return;LinearLayout f=form();f.addView(paragraph("Update the working notes without leaving the current job. Checklist items are added only when you explicitly select them."));EditText diagnosis=multi("Diagnosis",j.s("diagnosis"));EditText work=multi("Work performed",j.s("work_done"));EditText parts=multi("Parts / materials",j.s("parts"));f.addView(diagnosis);f.addView(work);MaterialButton checklist=outlineButton("Add service checklist");checklist.setOnClickListener(v->showServiceChecklist(work));f.addView(checklist);f.addView(parts);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Field notes & checklist").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save notes",null).create();d.setCanceledOnTouchOutside(false);d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{db.updateJobFieldNotes(jobId,val(diagnosis),val(work),val(parts));d.dismiss();toast("Field notes saved on this device");showJobDetail(jobId);}));d.show();
    }

    private String completionWarnings(AppDatabase.Row j){
        ArrayList<String> missing=new ArrayList<>();if(j.l("service_started_at_ms")<=0)missing.add("• Service timer was never started");if(j.s("work_done").trim().isEmpty())missing.add("• Work performed is empty");if(db.photos(j.id()).isEmpty())missing.add("• No job photo is attached");if(j.s("signature_path").trim().isEmpty())missing.add("• Customer signature is not captured");if(missing.isEmpty())return "";StringBuilder out=new StringBuilder("Before completing, note:\n");for(String m:missing)out.append(m).append('\n');out.append("\nYou can still complete the job if these items are not required for this service.");return out.toString();
    }

    private void showCompletionReview(long jobId){
        AppDatabase.Row j=db.getJob(jobId);if(j.id()==0)return;String warnings=completionWarnings(j);String summary="Customer: "+(j.s("customer_name").isEmpty()?"Not set":j.s("customer_name"))+"\nService duration: "+serviceDuration(j)+"\nPhotos: "+db.photos(jobId).size()+"\nSignature: "+(j.s("signature_path").isEmpty()?"Not captured":"Captured")+"\nWork notes: "+(j.s("work_done").trim().isEmpty()?"Not entered":"Recorded")+"\nSync status: "+jobSyncState(jobId);if(!warnings.isEmpty())summary+="\n\n"+warnings;String positive=warnings.isEmpty()?"Complete job":"Complete anyway";new MaterialAlertDialogBuilder(this).setTitle("Final review · "+j.s("report_no")).setMessage(summary).setNegativeButton("Not yet",null).setPositiveButton(positive,(d,w)->completeJobFromReview(jobId)).show();
    }

    private void completeJobFromReview(long jobId){
        AppDatabase.Row j=db.getJob(jobId);if(j.id()==0)return;long aid=parse(j.s("asset_id"));String ns=j.s("next_service");if(aid>0&&ns.isEmpty())ns=db.suggestNextService(aid,j.s("job_date"));db.completeJobService(jobId);if(aid>0)db.completeMaintenanceIfNeeded(aid,jobId,j.s("work_done"),ns);showJobCompletionSuccess(jobId);
    }

    private void showJobCompletionSuccess(long jobId){
        AppDatabase.Row j=db.getJob(jobId);if(j.id()==0){showJobs();return;}setHeader(j.s("report_no"),"Completed");clear();LinearLayout b=body(page());b.addView(heroCard("Job completed","The service record is locked for technician accounts and ready for reporting."));b.addView(info("Customer",j.s("customer_name")));b.addView(info("Service duration",serviceDuration(j)));b.addView(info("Photos",String.valueOf(db.photos(jobId).size())));b.addView(info("Signature",j.s("signature_path").isEmpty()?"Not captured":"Captured by "+j.s("customer_name_signed")));b.addView(info("Cloud status",jobSyncState(jobId)));if(db.jobSyncPendingCount(jobId)>0)b.addView(paragraph(networkAvailable()?"Changes are queued for workspace synchronization.":"You are offline. The completed job is saved safely on this device and will synchronize when connectivity is available."));MaterialButton view=button("View completed job");view.setOnClickListener(v->showJobDetail(jobId));b.addView(view);MaterialButton pdf=outlineButton("Generate & share PDF");pdf.setOnClickListener(v->generateAndShare(jobId));b.addView(pdf);MaterialButton jobs=outlineButton("Back to jobs");jobs.setOnClickListener(v->showJobs());b.addView(jobs);
    }

'''
replace_once(MAIN,'    private void showJobDetail(long id){\n',field_helpers+'    private void showJobDetail(long id){\n')

new_detail=r'''    private void showJobDetail(long id){
        AppDatabase.Row j=db.getJob(id);if(j.id()==0){toast("Job not found");return;}if(!canSeeJob(j)){toast("This job is not assigned to you");showJobs();return;}setHeader(j.s("report_no"),j.s("status"));clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Jobs");back.setOnClickListener(v->showJobs());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));top.addView(spacerH());boolean completed="Completed".equals(j.s("status"));boolean canModify=canPerformFieldWork()&&(!completed||accountTeam.canManageTeam());if(canModify){MaterialButton edit=button("Edit");edit.setOnClickListener(v->showJobDialog(id,0));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);if(completed&&!canModify)b.addView(empty("Locked — only an Owner or Admin can modify this completed service job."));
        b.addView(section(j.s("title")));b.addView(info("Customer",j.s("customer_name")));b.addView(info("Site",j.s("site_name")));b.addView(info("Asset",(j.s("asset_tag").isEmpty()?"":j.s("asset_tag")+" · ")+j.s("asset_name")));b.addView(info("Service date",j.s("job_date")));b.addView(info("Technician",j.s("technician")));if(canSeeAllJobs())b.addView(info("Assignment control","Owner/Admin · reassignment allowed"));b.addView(info("Priority",j.s("priority")));
        boolean serviceRunning=db.jobServiceRunning(id);JSONArray serviceSessions=db.jobServiceSessions(id);String timerState=completed?"Completed":serviceRunning?"Running":j.l("service_started_at_ms")>0?"Paused":"Not started";
        b.addView(section("Field work"));b.addView(info("Service state",timerState+" · "+serviceDuration(j)));b.addView(info("Cloud status",jobSyncState(id)));
        if(canModify&&!completed){MaterialButton timingAction=button(j.l("service_started_at_ms")<=0?"Start service now":serviceRunning?"Pause service":"Resume service");timingAction.setOnClickListener(v->{if(db.jobServiceRunning(id)){db.pauseJobService(id);toast("Service paused · progress saved locally");showJobDetail(id);}else startJobAndOpen(id);});b.addView(timingAction);LinearLayout quick=new LinearLayout(this);quick.setOrientation(LinearLayout.HORIZONTAL);MaterialButton notes=outlineButton("Notes & checklist");notes.setOnClickListener(v->showFieldNotesDialog(id));quick.addView(notes,new LinearLayout.LayoutParams(0,dp(50),1));quick.addView(spacerH());MaterialButton photo=outlineButton("Add photo");photo.setOnClickListener(v->capturePhoto(id));quick.addView(photo,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(quick);MaterialButton sig=outlineButton("Customer signature");sig.setOnClickListener(v->captureSignature(id));b.addView(sig);}
        b.addView(section("Service timing"));b.addView(info("Timer status",timerState));b.addView(info("First started",serviceTime(j.l("service_started_at_ms")).isEmpty()?"Not started":serviceTime(j.l("service_started_at_ms"))));b.addView(info("Finished",serviceTime(j.l("service_completed_at_ms")).isEmpty()?"Not finished":serviceTime(j.l("service_completed_at_ms"))));b.addView(info("Active service duration",serviceDuration(j)));b.addView(info("Work sessions",String.valueOf(serviceSessions.length())));if(serviceSessions.length()>0){b.addView(section("Work sessions"));for(int si=0;si<serviceSessions.length();si++){JSONObject ss=serviceSessions.optJSONObject(si);if(ss==null)continue;long st=ss.optLong("started_at_ms",0L),en=ss.optLong("ended_at_ms",0L),endForDuration=en>0?en:System.currentTimeMillis();String when=serviceTime(st)+" → "+(en>0?serviceTime(en):"Running");long mins=Math.max(0L,(endForDuration-st)/60000L);b.addView(rowCard("Session "+(si+1),when,compactMinutes(mins)));}}
        addIf(b,"Reported problem",j.s("problem"));addIf(b,"Diagnosis",j.s("diagnosis"));addIf(b,"Work performed",j.s("work_done"));addIf(b,"Parts / materials",j.s("parts"));addIf(b,"Next service",j.s("next_service"));
        b.addView(section("Evidence & acceptance"));b.addView(info("Photos",db.photos(id).size()+" attached"));b.addView(info("Signature",j.s("signature_path").isEmpty()?"Not captured":"Captured by "+j.s("customer_name_signed")));if(!canModify&&completed)b.addView(paragraph("Photos and customer signature are locked with the completed job. Ask an Owner or Admin if a correction is required."));
        b.addView(section("Assignment history"));List<AppDatabase.Row> assignmentHistory=db.assignmentHistory(id);if(assignmentHistory.isEmpty())b.addView(paragraph("No reassignment recorded yet."));else for(AppDatabase.Row h:assignmentHistory){String from=h.s("from_technician_name").isEmpty()?"Unassigned":h.s("from_technician_name");String to=h.s("to_technician_name").isEmpty()?"Unassigned":h.s("to_technician_name");String meta=h.s("changed_at")+(h.s("changed_by").isEmpty()?"":" • "+h.s("changed_by"));b.addView(rowCard(from+" → "+to,meta,h.i("pending")==1?"Pending sync":"Recorded"));}
        b.addView(section("Actions"));if(canSeeAllJobs()){MaterialButton reassign=outlineButton("Reassign job");reassign.setOnClickListener(v->showReassignJob(id));b.addView(reassign);}MaterialButton pdf=button("Generate & share PDF");pdf.setOnClickListener(v->generateAndShare(id));b.addView(pdf);if(canModify&&!completed){MaterialButton complete=outlineButton("Review & complete job");complete.setOnClickListener(v->showCompletionReview(id));b.addView(complete);}else b.addView(info("Status","Completed — ready for final reporting"));
    }

'''
replace_between(MAIN,'    private void showJobDetail(long id){','    private void showReassignJob(long jobId){',new_detail)

print('Fida Field 0.9.48 field workflow polish patch applied')
