from pathlib import Path


def rep(s, old, new, label):
    assert old in s, f"{label} anchor not found"
    return s.replace(old, new, 1)


# ---------- Local database ----------
p = Path("fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java")
s = p.read_text()
s = rep(s, "public static final int DB_VERSION = 8;", "public static final int DB_VERSION = 9;", "DB version")
s = rep(s, "import java.util.Map;", "import java.util.Map;\nimport java.util.Set;", "Set import")
s = rep(
    s,
    "parts TEXT, technician TEXT, priority TEXT DEFAULT 'Normal'",
    "parts TEXT, technician TEXT, technician_id INTEGER, priority TEXT DEFAULT 'Normal'",
    "jobs technician id schema",
)
anchor = '        db.execSQL("CREATE TABLE technicians (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT, phone TEXT, email TEXT, user_uuid TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL)");'
insert = anchor + '\n        db.execSQL("CREATE TABLE job_assignment_history (id INTEGER PRIMARY KEY AUTOINCREMENT, remote_uuid TEXT UNIQUE, job_id INTEGER NOT NULL, from_technician_id INTEGER, to_technician_id INTEGER, from_technician_name TEXT, to_technician_name TEXT, changed_by TEXT, changed_at TEXT NOT NULL, pending INTEGER DEFAULT 0, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)");\n        db.execSQL("CREATE INDEX idx_job_assignment_history_job ON job_assignment_history(job_id,changed_at)");\n        db.execSQL("CREATE INDEX idx_jobs_technician_id ON jobs(technician_id)");'
s = rep(s, anchor, insert, "assignment history onCreate")
old = '''        if(oldVersion<8){
            db.execSQL("ALTER TABLE technicians ADD COLUMN user_uuid TEXT");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_technicians_user_uuid ON technicians(user_uuid)");
        }
    }'''
new = '''        if(oldVersion<8){
            db.execSQL("ALTER TABLE technicians ADD COLUMN user_uuid TEXT");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_technicians_user_uuid ON technicians(user_uuid)");
        }
        if(oldVersion<9){
            db.execSQL("ALTER TABLE jobs ADD COLUMN technician_id INTEGER");
            db.execSQL("UPDATE jobs SET technician_id=(SELECT t.id FROM technicians t WHERE lower(trim(t.name))=lower(trim(jobs.technician)) ORDER BY t.id LIMIT 1) WHERE technician_id IS NULL AND technician IS NOT NULL AND trim(technician)<>''");
            db.execSQL("CREATE TABLE IF NOT EXISTS job_assignment_history (id INTEGER PRIMARY KEY AUTOINCREMENT, remote_uuid TEXT UNIQUE, job_id INTEGER NOT NULL, from_technician_id INTEGER, to_technician_id INTEGER, from_technician_name TEXT, to_technician_name TEXT, changed_by TEXT, changed_at TEXT NOT NULL, pending INTEGER DEFAULT 0, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_job_assignment_history_job ON job_assignment_history(job_id,changed_at)");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_jobs_technician_id ON jobs(technician_id)");
        }
    }'''
s = rep(s, old, new, "DB upgrade 9")
s = rep(
    s,
    'v.put("technician",j(o,"technician_name"));long cid=',
    'v.put("technician",j(o,"technician_name"));long tid=remoteLocal("technician",o,"technician_id");if(tid>0)v.put("technician_id",tid);else v.putNull("technician_id");long cid=',
    "remote job technician mapping",
)
old = '''    public long saveJob(long id, Map<String,String> m, String prefix) {
        ContentValues v=cv(m,"title","problem","diagnosis","work_done","parts","technician","priority","status","job_date","next_service","customer_name_signed"); putLong(v,"customer_id",m.get("customer_id")); putLong(v,"site_id",m.get("site_id")); putLong(v,"asset_id",m.get("asset_id")); v.put("updated_at",now());long saved=id;
        if(id==0){v.put("report_no",nextReportNo(prefix));v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("jobs",null,v);}else getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(id)});queueSync("job",saved,"upsert");return saved;
    }'''
new = '''    public long saveJob(long id, Map<String,String> m, String prefix) {
        Row before=id>0?one("SELECT technician_id,technician FROM jobs WHERE id=?",new String[]{String.valueOf(id)}):new Row();long oldTech=before.i("technician_id");
        ContentValues v=cv(m,"title","problem","diagnosis","work_done","parts","technician","priority","status","job_date","next_service","customer_name_signed"); putLong(v,"customer_id",m.get("customer_id")); putLong(v,"site_id",m.get("site_id")); putLong(v,"asset_id",m.get("asset_id")); putLong(v,"technician_id",m.get("technician_id")); v.put("updated_at",now());long saved=id;
        if(id==0){v.put("report_no",nextReportNo(prefix));v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("jobs",null,v);}else getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(id)});long newTech=0;try{newTech=Long.parseLong(m.getOrDefault("technician_id","0"));}catch(Exception ignored){}if(saved>0&&oldTech!=newTech)recordLocalAssignment(saved,oldTech,newTech,m.getOrDefault("assignment_actor","Local user"));queueSync("job",saved,"upsert");return saved;
    }'''
s = rep(s, old, new, "saveJob assignment id")
anchor = '    public List<Row> recentJobs(int limit) { return rows("SELECT j.*, c.name customer_name FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id ORDER BY j.job_date DESC,j.id DESC LIMIT " + limit, null); }'
extra = r'''

    private void appendJobScope(StringBuilder sql,ArrayList<String> args,String userUuid,boolean seeAll){if(!seeAll){sql.append(" AND EXISTS (SELECT 1 FROM technicians scope_t WHERE scope_t.id=j.technician_id AND scope_t.user_uuid=?)");args.add(userUuid==null?"":userUuid);}}
    public boolean jobVisibleToUser(long jobId,String userUuid,boolean seeAll){if(seeAll)return getJob(jobId).id()>0;return countSql("SELECT COUNT(*) FROM jobs j WHERE j.id=? AND EXISTS (SELECT 1 FROM technicians t WHERE t.id=j.technician_id AND t.user_uuid=?)",new String[]{String.valueOf(jobId),userUuid==null?"":userUuid})>0;}
    public long visibleOpenJobCount(String userUuid,boolean seeAll){if(seeAll)return count("jobs","status<>'Completed'",null);return countSql("SELECT COUNT(*) FROM jobs j WHERE j.status<>'Completed' AND EXISTS (SELECT 1 FROM technicians t WHERE t.id=j.technician_id AND t.user_uuid=?)",new String[]{userUuid==null?"":userUuid});}
    private long countSql(String sql,String[] args){Cursor c=getReadableDatabase().rawQuery(sql,args);try{return c.moveToFirst()?c.getLong(0):0;}finally{c.close();}}
    public List<Row> jobsFilteredScoped(String search,String status,String priority,String technician,String fromDate,String toDate,String userUuid,boolean seeAll){
        StringBuilder sql=new StringBuilder("SELECT j.*,c.name customer_name,s.name site_name,a.name asset_name,a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE 1=1");ArrayList<String> args=new ArrayList<>();appendJobScope(sql,args,userUuid,seeAll);
        if(status!=null&&!status.isEmpty()&&!status.equals("All")){sql.append(" AND j.status=?");args.add(status);}if(priority!=null&&!priority.isEmpty()&&!priority.equals("All")){sql.append(" AND j.priority=?");args.add(priority);}if(technician!=null&&!technician.isEmpty()&&!technician.equals("All")){if(technician.equals("Unassigned"))sql.append(" AND (j.technician IS NULL OR j.technician='')");else{sql.append(" AND j.technician=?");args.add(technician);}}if(fromDate!=null&&!fromDate.isEmpty()){sql.append(" AND j.job_date>=?");args.add(fromDate);}if(toDate!=null&&!toDate.isEmpty()){sql.append(" AND j.job_date<=?");args.add(toDate);}if(search!=null&&!search.trim().isEmpty()){sql.append(" AND (j.report_no LIKE ? OR j.title LIKE ? OR j.problem LIKE ? OR c.name LIKE ? OR s.name LIKE ? OR a.name LIKE ? OR a.tag LIKE ? OR j.technician LIKE ?)");String q="%"+search.trim()+"%";for(int i=0;i<8;i++)args.add(q);}sql.append(" ORDER BY j.job_date DESC,j.id DESC");return rows(sql.toString(),args.toArray(new String[0]));
    }
    public List<Row> jobsForCustomerScoped(long customerId,String userUuid,boolean seeAll){StringBuilder sql=new StringBuilder("SELECT j.*,c.name customer_name,s.name site_name,a.name asset_name,a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.customer_id=?");ArrayList<String> args=new ArrayList<>();args.add(String.valueOf(customerId));appendJobScope(sql,args,userUuid,seeAll);sql.append(" ORDER BY j.job_date DESC,j.id DESC");return rows(sql.toString(),args.toArray(new String[0]));}
    public List<Row> jobsForSiteScoped(long siteId,String userUuid,boolean seeAll){StringBuilder sql=new StringBuilder("SELECT j.*,c.name customer_name,s.name site_name,a.name asset_name,a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.site_id=?");ArrayList<String> args=new ArrayList<>();args.add(String.valueOf(siteId));appendJobScope(sql,args,userUuid,seeAll);sql.append(" ORDER BY j.job_date DESC,j.id DESC");return rows(sql.toString(),args.toArray(new String[0]));}
    public List<Row> jobsForAssetScoped(long assetId,String userUuid,boolean seeAll){StringBuilder sql=new StringBuilder("SELECT j.*,c.name customer_name FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id WHERE j.asset_id=?");ArrayList<String> args=new ArrayList<>();args.add(String.valueOf(assetId));appendJobScope(sql,args,userUuid,seeAll);sql.append(" ORDER BY j.job_date DESC,j.id DESC");return rows(sql.toString(),args.toArray(new String[0]));}
    public List<Row> recentJobsScoped(int limit,String userUuid,boolean seeAll){StringBuilder sql=new StringBuilder("SELECT j.*,c.name customer_name FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id WHERE 1=1");ArrayList<String> args=new ArrayList<>();appendJobScope(sql,args,userUuid,seeAll);sql.append(" ORDER BY j.job_date DESC,j.id DESC LIMIT ").append(Math.max(1,limit));return rows(sql.toString(),args.toArray(new String[0]));}
    public List<Row> maintenanceForAssetScoped(long assetId,String userUuid,boolean seeAll){if(seeAll)return maintenanceForAsset(assetId);return rows("SELECT m.*,j.report_no,j.title job_title FROM maintenance_logs m JOIN jobs j ON j.id=m.job_id JOIN technicians t ON t.id=j.technician_id WHERE m.asset_id=? AND t.user_uuid=? ORDER BY m.service_date DESC,m.id DESC",new String[]{String.valueOf(assetId),userUuid==null?"":userUuid});}

    private void recordLocalAssignment(long jobId,long fromTech,long toTech,String actor){String from=fromTech>0?getTechnician(fromTech).s("name"):"",to=toTech>0?getTechnician(toTech).s("name"):"";ContentValues v=new ContentValues();v.put("remote_uuid","local:"+java.util.UUID.randomUUID());v.put("job_id",jobId);if(fromTech>0)v.put("from_technician_id",fromTech);if(toTech>0)v.put("to_technician_id",toTech);v.put("from_technician_name",from);v.put("to_technician_name",to);v.put("changed_by",actor==null||actor.trim().isEmpty()?"Local user":actor.trim());v.put("changed_at",now());v.put("pending",1);getWritableDatabase().insert("job_assignment_history",null,v);}
    public void reassignJob(long jobId,long technicianId,String actor){Row job=getJob(jobId),tech=getTechnician(technicianId);if(job.id()==0||tech.id()==0)return;long old=job.i("technician_id");if(old==technicianId)return;ContentValues v=new ContentValues();v.put("technician_id",technicianId);v.put("technician",tech.s("name"));v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});recordLocalAssignment(jobId,old,technicianId,actor);queueSync("job",jobId,"upsert");}
    public List<Row> assignmentHistory(long jobId){return rows("SELECT * FROM job_assignment_history WHERE job_id=? ORDER BY changed_at DESC,id DESC",new String[]{String.valueOf(jobId)});}
    public void cacheAssignmentHistory(JSONArray items)throws Exception{SQLiteDatabase d=getWritableDatabase();for(int i=0;i<items.length();i++){JSONObject o=items.getJSONObject(i);String remote=j(o,"id");long jobId=localIdForRemote("job",j(o,"job_id"));if(remote.isEmpty()||jobId<=0)continue;long fromId=remoteLocal("technician",o,"from_technician_id"),toId=remoteLocal("technician",o,"to_technician_id");String from=j(o,"from_technician_name"),to=j(o,"to_technician_name");Row pending=one("SELECT * FROM job_assignment_history WHERE job_id=? AND pending=1 AND coalesce(from_technician_name,'')=? AND coalesce(to_technician_name,'')=? ORDER BY id DESC LIMIT 1",new String[]{String.valueOf(jobId),from,to});ContentValues v=new ContentValues();v.put("remote_uuid",remote);v.put("job_id",jobId);if(fromId>0)v.put("from_technician_id",fromId);else v.putNull("from_technician_id");if(toId>0)v.put("to_technician_id",toId);else v.putNull("to_technician_id");v.put("from_technician_name",from);v.put("to_technician_name",to);v.put("changed_by",j(o,"changed_by_name"));v.put("changed_at",j(o,"changed_at"));v.put("pending",0);if(pending.id()>0)d.update("job_assignment_history",v,"id=?",new String[]{String.valueOf(pending.id())});else d.insertWithOnConflict("job_assignment_history",null,v,SQLiteDatabase.CONFLICT_IGNORE);}}
    public void pruneInvisibleCloudJobs(Set<String> visibleRemoteIds){List<Row> linked=rows("SELECT entity_id,remote_uuid FROM sync_metadata WHERE entity_type='job' AND deleted_at IS NULL",null);SQLiteDatabase d=getWritableDatabase();for(Row m:linked){String remote=m.s("remote_uuid");long jobId=0;try{jobId=Long.parseLong(m.s("entity_id"));}catch(Exception ignored){}if(jobId<=0||visibleRemoteIds.contains(remote))continue;if(hasPendingSync("job",jobId)){recordSyncConflict("job",jobId,remote,"Job visibility changed in the workspace while this device has unsynced work");continue;}for(Row ph:rows("SELECT id FROM job_photos WHERE job_id=?",new String[]{String.valueOf(jobId)}))d.delete("sync_metadata","entity_type='job_photo' AND entity_id=?",new String[]{String.valueOf(ph.id())});for(Row ml:rows("SELECT id FROM maintenance_logs WHERE job_id=?",new String[]{String.valueOf(jobId)})){d.delete("sync_metadata","entity_type='maintenance_log' AND entity_id=?",new String[]{String.valueOf(ml.id())});d.delete("maintenance_logs","id=?",new String[]{String.valueOf(ml.id())});}d.delete("job_assignment_history","job_id=?",new String[]{String.valueOf(jobId)});d.delete("sync_metadata","entity_type='job_signature' AND entity_id=?",new String[]{String.valueOf(jobId)});d.delete("jobs","id=?",new String[]{String.valueOf(jobId)});d.delete("sync_metadata","entity_type='job' AND entity_id=?",new String[]{String.valueOf(jobId)});resolveSyncConflict("job",jobId);}}
'''
s = rep(s, anchor, anchor + extra, "scoped job methods")
s = s.replace('String[] tables={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","sequences"};', 'String[] tables={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};', 1)
s = s.replace('String[] tables={"maintenance_logs","job_photos","jobs","assets","sites","customers","technicians","sequences"};', 'String[] tables={"job_assignment_history","maintenance_logs","job_photos","jobs","assets","sites","customers","technicians","sequences"};', 1)
s = s.replace('String[] order={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","sequences"};', 'String[] order={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};', 1)
p.write_text(s)


# ---------- Cloud sync ----------
p = Path("fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java")
s = p.read_text()
old = '''            int pushed=0,pulled=0,deferred=0;String[] pushOrder={"customer","site","asset","technician","job"};String[] deleteOrder={"job","asset","site","customer","technician"};List<AppDatabase.Row> pending=db.pendingBusinessSyncRows();'''
new = '''            int pushed=0,pulled=0,deferred=0;String[] pushOrder={"customer","site","asset","technician","job"};String[] deleteOrder={"job","asset","site","customer","technician"};List<AppDatabase.Row> pending=db.pendingBusinessSyncRows();java.util.ArrayList<Long> finalizeCompleted=new java.util.ArrayList<>();java.util.HashSet<String> visibleJobIds=new java.util.HashSet<>();'''
s = rep(s, old, new, "sync state")
old = 'String remoteId=body.optString("id");client.upsert(tableFor(type),"id",body);db.markEntitySynced(type,localId,remoteId);pushed++;'
new = 'String remoteId=body.optString("id");if("job".equals(type)&&!canManage&&"Completed".equals(body.optString("status"))){JSONObject staged=new JSONObject(body.toString());staged.put("status","In Progress");client.upsert(tableFor(type),"id",staged);db.bindRemoteUuid(type,localId,remoteId);finalizeCompleted.add(localId);}else{client.upsert(tableFor(type),"id",body);db.markEntitySynced(type,localId,remoteId);}pushed++;'
s = rep(s, old, new, "completed staging")
s = rep(s, 'if(remote.isEmpty())continue;if(isDeleted(o)){', 'if(remote.isEmpty())continue;if("job".equals(type))visibleJobIds.add(remote);if(isDeleted(o)){', "visible job ids")
old = '''            syncBranding(workspaceId,canManage);
            CloudMediaSync.Result media=new CloudMediaSync(context,prefs,db,client).sync(workspaceId,canManage);
            refreshTeamCache(workspaceId,canManage);'''
new = '''            if(!canManage)db.pruneInvisibleCloudJobs(visibleJobIds);
            syncBranding(workspaceId,canManage);
            CloudMediaSync.Result media=new CloudMediaSync(context,prefs,db,client).sync(workspaceId,canManage);
            for(Long localId:finalizeCompleted){JSONObject finalBody=payload("job",localId,workspaceId);if(finalBody!=null){client.upsert("jobs","id",finalBody);db.markEntitySynced("job",localId,finalBody.optString("id"));}}
            syncAssignmentHistory(workspaceId);
            refreshTeamCache(workspaceId,canManage);'''
s = rep(s, old, new, "post media finalize")
s = rep(s, 'o.put("technician_name",r.s("technician"));putDate(o,"job_date",r.s("job_date"));', 'o.put("technician_name",r.s("technician"));putRemoteRef(o,"technician_id","technician",r.s("technician_id"));putDate(o,"job_date",r.s("job_date"));', "job payload technician id")
anchor = '    private void syncBranding(String workspaceId,boolean canManage)throws Exception{'
method = '    private void syncAssignmentHistory(String workspaceId)throws Exception{JSONArray history=client.select("job_assignment_history","select=*&workspace_id=eq."+workspaceId+"&order=changed_at.asc");db.cacheAssignmentHistory(history);}\n\n'
s = rep(s, anchor, method + anchor, "assignment history pull")
p.write_text(s)


# ---------- UI ----------
p = Path("fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java")
s = p.read_text()
anchor = '    private void clear(){content.removeAllViews();}'
helpers = '''    private boolean canSeeAllJobs(){return accountTeam!=null&&accountTeam.canManageTeam();}
    private String currentJobUserUuid(){return accountTeam==null?"":accountTeam.cloudUserId();}
    private long myTechnicianId(){AppDatabase.Row t=db.technicianForUser(currentJobUserUuid());return t.id();}
    private boolean canSeeJob(AppDatabase.Row job){return job!=null&&job.id()>0&&db.jobVisibleToUser(job.id(),currentJobUserUuid(),canSeeAllJobs());}
'''
s = rep(s, anchor, anchor + "\n" + helpers, "job visibility helpers")
s = s.replace('db.count("jobs","status<>\'Completed\'",null)', 'db.visibleOpenJobCount(currentJobUserUuid(),canSeeAllJobs())', 1)
s = s.replace('List<AppDatabase.Row> recent=db.recentJobs(4);', 'List<AppDatabase.Row> recent=db.recentJobsScoped(4,currentJobUserUuid(),canSeeAllJobs());', 1)
s = s.replace('Spinner technician=spinner(technicianFilterValues());', 'Spinner technician=spinner(canSeeAllJobs()?technicianFilterValues():new String[]{"My assigned jobs"});', 1)
old = 'private void renderJobs(LinearLayout list,String q,String status,String priority,String technician,String from,String to){list.removeAllViews();List<AppDatabase.Row> rows=db.jobsFiltered(q,status,priority,technician,from,to);'
new = 'private void renderJobs(LinearLayout list,String q,String status,String priority,String technician,String from,String to){list.removeAllViews();String techFilter=canSeeAllJobs()?technician:"All";List<AppDatabase.Row> rows=db.jobsFilteredScoped(q,status,priority,techFilter,from,to,currentJobUserUuid(),canSeeAllJobs());'
s = rep(s, old, new, "jobs list scope")
s = s.replace('long jobs=db.count("jobs","customer_id=?",new String[]{String.valueOf(r.id())});', 'long jobs=db.jobsForCustomerScoped(r.id(),currentJobUserUuid(),canSeeAllJobs()).size();', 1)
s = s.replace('stat("Jobs",db.count("jobs","customer_id=?",new String[]{String.valueOf(id)}))', 'stat("Jobs",db.jobsForCustomerScoped(id,currentJobUserUuid(),canSeeAllJobs()).size())', 1)
s = s.replace('List<AppDatabase.Row> jobs=db.jobsForCustomer(id);', 'List<AppDatabase.Row> jobs=db.jobsForCustomerScoped(id,currentJobUserUuid(),canSeeAllJobs());', 1)
s = s.replace('List<AppDatabase.Row> assets=db.assets(0,id);List<AppDatabase.Row> jobs=db.jobsForSite(id);', 'List<AppDatabase.Row> assets=db.assets(0,id);List<AppDatabase.Row> jobs=db.jobsForSiteScoped(id,currentJobUserUuid(),canSeeAllJobs());', 1)
s = s.replace('List<AppDatabase.Row> jobs=db.jobsForAsset(id);', 'List<AppDatabase.Row> jobs=db.jobsForAssetScoped(id,currentJobUserUuid(),canSeeAllJobs());', 1)
s = s.replace('List<AppDatabase.Row> logs=db.maintenanceForAsset(id);', 'List<AppDatabase.Row> logs=db.maintenanceForAssetScoped(id,currentJobUserUuid(),canSeeAllJobs());', 1)
s = s.replace('List<AppDatabase.Row> rows=db.jobs("","Completed");', 'List<AppDatabase.Row> rows=db.jobsFilteredScoped("","Completed","All","All","","",currentJobUserUuid(),canSeeAllJobs());', 1)
s = s.replace('for(AppDatabase.Row r:db.jobsFiltered("","All","All","All","",""))', 'for(AppDatabase.Row r:db.jobsFilteredScoped("","All","All","All","","",currentJobUserUuid(),canSeeAllJobs()))', 1)
old = '''        AppDatabase.Row r=id>0?db.getJob(id):new AppDatabase.Row();
        if(id>0&&"Completed".equals(r.s("status"))&&!accountTeam.canManageTeam()){new MaterialAlertDialogBuilder(this).setTitle("Completed job locked").setMessage("Only an Owner or Admin can modify a completed service job.").setPositiveButton("OK",null).show();return;}
        AppDatabase.Row ar='''
new = '''        AppDatabase.Row r=id>0?db.getJob(id):new AppDatabase.Row();
        if(id>0&&!canSeeJob(r)){new MaterialAlertDialogBuilder(this).setTitle("Job not available").setMessage("You can only access service jobs assigned to your workspace person profile.").setPositiveButton("OK",null).show();return;}
        if(id>0&&"Completed".equals(r.s("status"))&&!accountTeam.canManageTeam()){new MaterialAlertDialogBuilder(this).setTitle("Completed job locked").setMessage("Only an Owner or Admin can modify a completed service job.").setPositiveButton("OK",null).show();return;}
        boolean manager=canSeeAllJobs();long ownTech=myTechnicianId();if(id==0&&!manager&&ownTech<=0){new MaterialAlertDialogBuilder(this).setTitle("Field assignment required").setMessage("Your workspace account is not linked to an active field person. Ask an Owner or Admin to enable field job assignment for your People & Team profile.").setPositiveButton("OK",null).show();return;}
        AppDatabase.Row ar='''
s = rep(s, old, new, "job dialog access")
old = 'String currentTech=id>0?r.s("technician"):prefs.getString("technician_name","");Spinner tech=choiceSpinner(technicianChoices(true,currentTech));setChoiceByLabel(tech,currentTech);'
new = 'String currentTech=id>0?r.s("technician"):prefs.getString("technician_name","");long currentTechId=id>0?parse(r.s("technician_id")):(manager?0:ownTech);List<Choice> jobTechChoices;if(manager)jobTechChoices=technicianChoices(true,currentTech);else{jobTechChoices=new ArrayList<>();AppDatabase.Row me=db.getTechnician(ownTech);jobTechChoices.add(new Choice(ownTech,me.s("name")));}Spinner tech=choiceSpinner(jobTechChoices);if(currentTechId>0)setChoice(tech,currentTechId);else setChoiceByLabel(tech,currentTech);tech.setEnabled(manager);'
s = rep(s, old, new, "assignment selector")
s = rep(s, '"technician",choiceLabel(tech),"priority"', '"technician",choiceLabel(tech),"technician_id",String.valueOf(((Choice)tech.getSelectedItem()).id),"assignment_actor",accountTeam.accountName(),"priority"', "job map technician id")
old = '        AppDatabase.Row j=db.getJob(id);if(j.id()==0){toast("Job not found");return;}setHeader'
new = '        AppDatabase.Row j=db.getJob(id);if(j.id()==0){toast("Job not found");return;}if(!canSeeJob(j)){toast("This job is not assigned to you");showJobs();return;}setHeader'
s = rep(s, old, new, "job detail gate")
s = rep(s, 'b.addView(info("Technician",j.s("technician")));', 'b.addView(info("Technician",j.s("technician")));if(canSeeAllJobs())b.addView(info("Assignment control","Owner/Admin · reassignment allowed"));', "assignment control info")
anchor = '        addIf(b,"Reported problem",j.s("problem"));addIf(b,"Diagnosis",j.s("diagnosis"));addIf(b,"Work performed",j.s("work_done"));addIf(b,"Parts / materials",j.s("parts"));addIf(b,"Next service",j.s("next_service"));'
history = anchor + '\n        b.addView(section("Assignment history"));List<AppDatabase.Row> assignmentHistory=db.assignmentHistory(id);if(assignmentHistory.isEmpty())b.addView(paragraph("No reassignment recorded yet."));else for(AppDatabase.Row h:assignmentHistory){String from=h.s("from_technician_name").isEmpty()?"Unassigned":h.s("from_technician_name");String to=h.s("to_technician_name").isEmpty()?"Unassigned":h.s("to_technician_name");String meta=h.s("changed_at")+(h.s("changed_by").isEmpty()?"":" • "+h.s("changed_by"));b.addView(rowCard(from+" → "+to,meta,h.i("pending")==1?"Pending sync":"Recorded"));}'
s = rep(s, anchor, history, "assignment history UI")
s = rep(s, 'b.addView(section("Actions"));MaterialButton pdf=button("Generate & share PDF");', 'b.addView(section("Actions"));if(canSeeAllJobs()){MaterialButton reassign=outlineButton("Reassign job");reassign.setOnClickListener(v->showReassignJob(id));b.addView(reassign);}MaterialButton pdf=button("Generate & share PDF");', "reassign action")
anchor = '    private void capturePhoto(long jobId){'
method = '''    private void showReassignJob(long jobId){if(!canSeeAllJobs()){toast("Only Owner or Admin can reassign jobs");return;}AppDatabase.Row job=db.getJob(jobId);if(job.id()==0)return;ArrayList<Choice> choices=new ArrayList<>();for(AppDatabase.Row t:db.activeTechnicians())choices.add(new Choice(t.id(),t.s("name")+(t.s("user_uuid").isEmpty()?" · field only":" · app member")));if(choices.isEmpty()){toast("No active field people available");return;}LinearLayout f=form();Spinner tech=choiceSpinner(choices);setChoice(tech,parse(job.s("technician_id")));f.addView(label("Assign to"));f.addView(tech);f.addView(paragraph("The previous and new assignee are retained in Assignment history. The previous assignee loses access after cloud synchronization; the new assignee receives the job on their next sync."));AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Reassign "+job.s("report_no")).setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Reassign",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{Choice selected=(Choice)tech.getSelectedItem();if(selected==null||selected.id<=0)return;if(selected.id==parse(job.s("technician_id"))){toast("Job is already assigned to this person");return;}db.reassignJob(jobId,selected.id,accountTeam.accountName().isEmpty()?accountTeam.accountEmail():accountTeam.accountName());d.dismiss();toast("Job reassigned · queued for sync");showJobDetail(jobId);}));d.show();}

'''
s = rep(s, anchor, method + anchor, "reassign dialog")
old = '        String[] actions={"Create service job","Mark serviced now","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else if(which==1)showQuickMaintenanceDialog(asset);else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();'
new = '        if(canSeeAllJobs()){String[] actions={"Create service job","Mark serviced now","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else if(which==1)showQuickMaintenanceDialog(asset);else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}else{String[] actions={"Create my service job","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}'
s = rep(s, old, new, "maintenance action role")
s = s.replace('Fida Field 0.9.14 Test\\nCompleted-job role locking, workspace billing and reliable Supabase sync by Fidalix.', 'Fida Field 0.9.15 Test\\nAssignment-scoped jobs, manager reassignment history and reliable Supabase sync by Fidalix.', 1)
p.write_text(s)


# ---------- Version ----------
p = Path("fida-field/app/build.gradle")
g = p.read_text()
assert "versionCode 17" in g and "versionName '0.9.14-test'" in g, "version anchors not found"
g = g.replace("versionCode 17", "versionCode 18", 1).replace("versionName '0.9.14-test'", "versionName '0.9.15-test'", 1)
p.write_text(g)
