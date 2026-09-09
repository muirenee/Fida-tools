package com.fidalix.fidafield;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class AppDatabase extends SQLiteOpenHelper {
    public static final String DB_NAME = "fida_field.db";
    public static final int DB_VERSION = 4;

    public static class Row extends HashMap<String, String> {
        public long id() { try { return Long.parseLong(getOrDefault("id", "0")); } catch (Exception e) { return 0; } }
        public String s(String k) { return getOrDefault(k, ""); }
        public int i(String k) { try { return Integer.parseInt(getOrDefault(k, "0")); } catch (Exception e) { return 0; } }
    }

    public AppDatabase(Context context) { super(context, DB_NAME, null, DB_VERSION); }

    @Override public void onConfigure(SQLiteDatabase db) {
        super.onConfigure(db);
        db.setForeignKeyConstraintsEnabled(true);
    }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, contact TEXT, phone TEXT, email TEXT, address TEXT, notes TEXT, created_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE sites (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, name TEXT NOT NULL, address TEXT, contact TEXT, phone TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE)");
        db.execSQL("CREATE TABLE assets (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, site_id INTEGER, tag TEXT NOT NULL UNIQUE, name TEXT NOT NULL, category TEXT, make_model TEXT, serial TEXT, location TEXT, notes TEXT, interval_days INTEGER DEFAULT 0, next_service TEXT, created_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE SET NULL)");
        db.execSQL("CREATE TABLE jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, report_no TEXT NOT NULL UNIQUE, customer_id INTEGER, site_id INTEGER, asset_id INTEGER, title TEXT NOT NULL, problem TEXT, diagnosis TEXT, work_done TEXT, parts TEXT, technician TEXT, priority TEXT DEFAULT 'Normal', status TEXT DEFAULT 'Open', job_date TEXT NOT NULL, next_service TEXT, signature_path TEXT, customer_name_signed TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE SET NULL, FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE SET NULL)");
        db.execSQL("CREATE TABLE job_photos (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, uri TEXT NOT NULL, caption TEXT, created_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)");
        db.execSQL("CREATE TABLE maintenance_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id INTEGER NOT NULL, job_id INTEGER, service_date TEXT NOT NULL, notes TEXT, next_service TEXT, created_at TEXT NOT NULL, FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE SET NULL)");
        db.execSQL("CREATE TABLE technicians (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT, phone TEXT, email TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE sequences (year INTEGER PRIMARY KEY, seq INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE sync_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, operation TEXT NOT NULL DEFAULT 'upsert', changed_at TEXT NOT NULL, UNIQUE(entity_type,entity_id))");
        db.execSQL("CREATE TABLE workspace_members (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, member_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL, email TEXT, role TEXT NOT NULL DEFAULT 'Technician', status TEXT NOT NULL DEFAULT 'Active', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE workspace_invites (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, invite_uuid TEXT NOT NULL UNIQUE, email TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Technician', status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE sync_metadata (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, remote_uuid TEXT NOT NULL UNIQUE, server_version INTEGER DEFAULT 0, last_synced_at TEXT, deleted_at TEXT, UNIQUE(entity_type,entity_id))");
        db.execSQL("CREATE INDEX idx_workspace_members_workspace ON workspace_members(workspace_id,status)");
        db.execSQL("CREATE INDEX idx_workspace_invites_workspace ON workspace_invites(workspace_id,status)");
        db.execSQL("CREATE INDEX idx_jobs_date ON jobs(job_date)");
        db.execSQL("CREATE INDEX idx_assets_next_service ON assets(next_service)");
    }

    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        if(oldVersion<2){
            db.execSQL("CREATE TABLE IF NOT EXISTS technicians (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT, phone TEXT, email TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL)");
        }
        if(oldVersion<3){
            db.execSQL("CREATE TABLE IF NOT EXISTS sync_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, operation TEXT NOT NULL DEFAULT 'upsert', changed_at TEXT NOT NULL, UNIQUE(entity_type,entity_id))");
            String stamp=now();
            queueExistingForSync(db,"customer","customers",stamp);
            queueExistingForSync(db,"site","sites",stamp);
            queueExistingForSync(db,"asset","assets",stamp);
            queueExistingForSync(db,"job","jobs",stamp);
            queueExistingForSync(db,"technician","technicians",stamp);
        }
        if(oldVersion<4){
            db.execSQL("CREATE TABLE IF NOT EXISTS workspace_members (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, member_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL, email TEXT, role TEXT NOT NULL DEFAULT 'Technician', status TEXT NOT NULL DEFAULT 'Active', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)");
            db.execSQL("CREATE TABLE IF NOT EXISTS workspace_invites (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, invite_uuid TEXT NOT NULL UNIQUE, email TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Technician', status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)");
            db.execSQL("CREATE TABLE IF NOT EXISTS sync_metadata (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, remote_uuid TEXT NOT NULL UNIQUE, server_version INTEGER DEFAULT 0, last_synced_at TEXT, deleted_at TEXT, UNIQUE(entity_type,entity_id))");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id,status)");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_workspace_invites_workspace ON workspace_invites(workspace_id,status)");
        }
    }

    public String today() { return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date()); }
    public String now() { return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date()); }

    private void queueExistingForSync(SQLiteDatabase db,String type,String table,String stamp){
        db.execSQL("INSERT OR REPLACE INTO sync_queue(entity_type,entity_id,operation,changed_at) SELECT ?,id,'upsert',? FROM "+table,new Object[]{type,stamp});
    }
    private void queueSync(String type,long id,String operation){
        if(id<=0)return;ContentValues v=new ContentValues();v.put("entity_type",type);v.put("entity_id",id);v.put("operation",operation==null?"upsert":operation);v.put("changed_at",now());getWritableDatabase().insertWithOnConflict("sync_queue",null,v,SQLiteDatabase.CONFLICT_REPLACE);
    }

    public void ensureOwnerMember(String workspaceId,String name,String email){
        if(workspaceId==null||workspaceId.isEmpty())return;Row existing=one("SELECT * FROM workspace_members WHERE workspace_id=? AND role='Owner' LIMIT 1",new String[]{workspaceId});
        ContentValues v=new ContentValues();v.put("workspace_id",workspaceId);v.put("name",name==null||name.trim().isEmpty()?"Workspace owner":name.trim());v.put("email",email==null?"":email.trim());v.put("role","Owner");v.put("status","Active");v.put("updated_at",now());
        long saved;if(existing.id()>0){saved=existing.id();getWritableDatabase().update("workspace_members",v,"id=?",new String[]{String.valueOf(saved)});}else{v.put("member_uuid",java.util.UUID.randomUUID().toString());v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("workspace_members",null,v);}queueSync("workspace_member",saved,"upsert");
    }
    public List<Row> workspaceMembers(String workspaceId){return rows("SELECT * FROM workspace_members WHERE workspace_id=? ORDER BY CASE role WHEN 'Owner' THEN 0 WHEN 'Admin' THEN 1 WHEN 'Technician' THEN 2 ELSE 3 END,name COLLATE NOCASE",new String[]{workspaceId==null?"":workspaceId});}
    public Row getWorkspaceMember(long id){return one("SELECT * FROM workspace_members WHERE id=?",new String[]{String.valueOf(id)});}
    public long saveWorkspaceMember(long id,String workspaceId,String name,String email,String role,String status){ContentValues v=new ContentValues();v.put("workspace_id",workspaceId);v.put("name",name);v.put("email",email);v.put("role",role);v.put("status",status);v.put("updated_at",now());long saved=id;if(id==0){v.put("member_uuid",java.util.UUID.randomUUID().toString());v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("workspace_members",null,v);}else getWritableDatabase().update("workspace_members",v,"id=?",new String[]{String.valueOf(id)});queueSync("workspace_member",saved,"upsert");return saved;}
    public int activeWorkspaceMemberCount(String workspaceId){return (int)count("workspace_members","workspace_id=? AND status='Active'",new String[]{workspaceId});}
    public List<Row> workspaceInvites(String workspaceId){return rows("SELECT * FROM workspace_invites WHERE workspace_id=? ORDER BY CASE status WHEN 'Pending' THEN 0 ELSE 1 END,created_at DESC",new String[]{workspaceId==null?"":workspaceId});}
    public int pendingWorkspaceInviteCount(String workspaceId){return (int)count("workspace_invites","workspace_id=? AND status='Pending'",new String[]{workspaceId});}
    public long saveWorkspaceInvite(String workspaceId,String email,String role){Row old=one("SELECT * FROM workspace_invites WHERE workspace_id=? AND email=? AND status='Pending' LIMIT 1",new String[]{workspaceId,email});ContentValues v=new ContentValues();v.put("workspace_id",workspaceId);v.put("email",email);v.put("role",role);v.put("status","Pending");v.put("updated_at",now());long saved=old.id();if(saved>0)getWritableDatabase().update("workspace_invites",v,"id=?",new String[]{String.valueOf(saved)});else{v.put("invite_uuid",java.util.UUID.randomUUID().toString());v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("workspace_invites",null,v);}queueSync("workspace_invite",saved,"upsert");return saved;}
    public void cancelWorkspaceInvite(long id){ContentValues v=new ContentValues();v.put("status","Cancelled");v.put("updated_at",now());getWritableDatabase().update("workspace_invites",v,"id=?",new String[]{String.valueOf(id)});queueSync("workspace_invite",id,"upsert");}
    public String ensureRemoteUuid(String type,long entityId){Row r=one("SELECT remote_uuid FROM sync_metadata WHERE entity_type=? AND entity_id=?",new String[]{type,String.valueOf(entityId)});if(!r.s("remote_uuid").isEmpty())return r.s("remote_uuid");String uuid=java.util.UUID.randomUUID().toString();ContentValues v=new ContentValues();v.put("entity_type",type);v.put("entity_id",entityId);v.put("remote_uuid",uuid);getWritableDatabase().insertWithOnConflict("sync_metadata",null,v,SQLiteDatabase.CONFLICT_IGNORE);return one("SELECT remote_uuid FROM sync_metadata WHERE entity_type=? AND entity_id=?",new String[]{type,String.valueOf(entityId)}).s("remote_uuid");}
    public List<Row> pendingSyncRows(){return rows("SELECT q.*,m.remote_uuid,m.server_version,m.last_synced_at FROM sync_queue q LEFT JOIN sync_metadata m ON m.entity_type=q.entity_type AND m.entity_id=q.entity_id ORDER BY q.changed_at,q.id",null);}

    public long count(String table, String where, String[] args) {
        Cursor c = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM " + table + (where == null || where.isEmpty() ? "" : " WHERE " + where), args);
        try { return c.moveToFirst() ? c.getLong(0) : 0; } finally { c.close(); }
    }

    private Row cursorToRow(Cursor c) {
        Row r = new Row();
        for (int i = 0; i < c.getColumnCount(); i++) r.put(c.getColumnName(i), c.isNull(i) ? "" : c.getString(i));
        return r;
    }

    public Row one(String sql, String[] args) {
        Cursor c = getReadableDatabase().rawQuery(sql, args);
        try { return c.moveToFirst() ? cursorToRow(c) : new Row(); } finally { c.close(); }
    }

    public List<Row> rows(String sql, String[] args) {
        ArrayList<Row> out = new ArrayList<>();
        Cursor c = getReadableDatabase().rawQuery(sql, args);
        try { while (c.moveToNext()) out.add(cursorToRow(c)); } finally { c.close(); }
        return out;
    }

    public Row getCustomer(long id) { return one("SELECT * FROM customers WHERE id=?", new String[]{String.valueOf(id)}); }
    public Row getSite(long id) { return one("SELECT * FROM sites WHERE id=?", new String[]{String.valueOf(id)}); }
    public Row getAsset(long id) { return one("SELECT * FROM assets WHERE id=?", new String[]{String.valueOf(id)}); }
    public Row getAssetByTag(String tag) { return one("SELECT a.*, c.name customer_name, s.name site_name FROM assets a LEFT JOIN customers c ON c.id=a.customer_id LEFT JOIN sites s ON s.id=a.site_id WHERE a.tag=? COLLATE NOCASE", new String[]{tag==null?"":tag.trim()}); }

    public Row getTechnician(long id) { return one("SELECT * FROM technicians WHERE id=?", new String[]{String.valueOf(id)}); }
    public List<Row> technicians() { return rows("SELECT * FROM technicians ORDER BY active DESC,name COLLATE NOCASE", null); }
    public List<Row> activeTechnicians() { return rows("SELECT * FROM technicians WHERE active=1 ORDER BY name COLLATE NOCASE", null); }
    public long saveTechnician(long id, Map<String,String> m) {
        ContentValues v=cv(m,"name","role","phone","email"); putInt(v,"active",m.get("active"));long saved=id;
        if(id==0){v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("technicians",null,v);}else getWritableDatabase().update("technicians",v,"id=?",new String[]{String.valueOf(id)});queueSync("technician",saved,"upsert");return saved;
    }
    public List<Row> jobsForAsset(long assetId){return rows("SELECT j.*,c.name customer_name FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id WHERE j.asset_id=? ORDER BY j.job_date DESC,j.id DESC",new String[]{String.valueOf(assetId)});}
    public List<Row> maintenanceForAsset(long assetId){return rows("SELECT m.*,j.report_no,j.title job_title FROM maintenance_logs m LEFT JOIN jobs j ON j.id=m.job_id WHERE m.asset_id=? ORDER BY m.service_date DESC,m.id DESC",new String[]{String.valueOf(assetId)});}
    public String suggestNextService(long assetId,String fromDate){Row a=getAsset(assetId);int days=a.i("interval_days");if(days<=0)return "";try{SimpleDateFormat f=new SimpleDateFormat("yyyy-MM-dd",Locale.US);Date d=f.parse(fromDate==null||fromDate.isEmpty()?today():fromDate);Calendar c=Calendar.getInstance();c.setTime(d==null?new Date():d);c.add(Calendar.DAY_OF_YEAR,days);return f.format(c.getTime());}catch(Exception e){return "";}}

    public Row getJob(long id) {
        return one("SELECT j.*, c.name customer_name, s.name site_name, a.name asset_name, a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.id=?", new String[]{String.valueOf(id)});
    }

    public List<Row> customers() { return rows("SELECT * FROM customers ORDER BY name COLLATE NOCASE", null); }
    public List<Row> sites(long customerId) {
        return rows("SELECT s.*, c.name customer_name FROM sites s LEFT JOIN customers c ON c.id=s.customer_id " + (customerId > 0 ? "WHERE s.customer_id=? " : "") + "ORDER BY c.name,s.name", customerId > 0 ? new String[]{String.valueOf(customerId)} : null);
    }
    public List<Row> assets(long customerId, long siteId) {
        String where = ""; ArrayList<String> a = new ArrayList<>();
        if (customerId > 0) { where += " AND a.customer_id=?"; a.add(String.valueOf(customerId)); }
        if (siteId > 0) { where += " AND a.site_id=?"; a.add(String.valueOf(siteId)); }
        return rows("SELECT a.*, c.name customer_name, s.name site_name FROM assets a LEFT JOIN customers c ON c.id=a.customer_id LEFT JOIN sites s ON s.id=a.site_id WHERE 1=1" + where + " ORDER BY a.name COLLATE NOCASE", a.toArray(new String[0]));
    }
    public List<Row> jobs(String search, String status) { return jobsFiltered(search,status,"All","All","",""); }
    public List<Row> jobsFiltered(String search,String status,String priority,String technician,String fromDate,String toDate) {
        StringBuilder sql = new StringBuilder("SELECT j.*, c.name customer_name, s.name site_name, a.name asset_name, a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE 1=1");
        ArrayList<String> args = new ArrayList<>();
        if (status != null && !status.isEmpty() && !status.equals("All")) { sql.append(" AND j.status=?"); args.add(status); }
        if (priority != null && !priority.isEmpty() && !priority.equals("All")) { sql.append(" AND j.priority=?"); args.add(priority); }
        if (technician != null && !technician.isEmpty() && !technician.equals("All")) {
            if (technician.equals("Unassigned")) sql.append(" AND (j.technician IS NULL OR j.technician='')");
            else { sql.append(" AND j.technician=?"); args.add(technician); }
        }
        if (fromDate != null && !fromDate.isEmpty()) { sql.append(" AND j.job_date>=?"); args.add(fromDate); }
        if (toDate != null && !toDate.isEmpty()) { sql.append(" AND j.job_date<=?"); args.add(toDate); }
        if (search != null && !search.trim().isEmpty()) {
            sql.append(" AND (j.report_no LIKE ? OR j.title LIKE ? OR j.problem LIKE ? OR c.name LIKE ? OR s.name LIKE ? OR a.name LIKE ? OR a.tag LIKE ? OR j.technician LIKE ?)");
            String q="%"+search.trim()+"%"; for(int i=0;i<8;i++) args.add(q);
        }
        sql.append(" ORDER BY j.job_date DESC,j.id DESC");
        return rows(sql.toString(), args.toArray(new String[0]));
    }
    public List<Row> jobsForCustomer(long customerId){return rows("SELECT j.*,c.name customer_name,s.name site_name,a.name asset_name,a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.customer_id=? ORDER BY j.job_date DESC,j.id DESC",new String[]{String.valueOf(customerId)});}
    public List<Row> jobsForSite(long siteId){return rows("SELECT j.*,c.name customer_name,s.name site_name,a.name asset_name,a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.site_id=? ORDER BY j.job_date DESC,j.id DESC",new String[]{String.valueOf(siteId)});}
    public List<Row> recentJobs(int limit) { return rows("SELECT j.*, c.name customer_name FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id ORDER BY j.job_date DESC,j.id DESC LIMIT " + limit, null); }

    public List<Row> dueAssets(int days) {
        Calendar cal=Calendar.getInstance(); cal.add(Calendar.DAY_OF_YEAR, days);
        String until=new SimpleDateFormat("yyyy-MM-dd",Locale.US).format(cal.getTime());
        return rows("SELECT a.*, c.name customer_name, s.name site_name FROM assets a LEFT JOIN customers c ON c.id=a.customer_id LEFT JOIN sites s ON s.id=a.site_id WHERE a.next_service<>'' AND a.next_service IS NOT NULL AND a.next_service<=? ORDER BY a.next_service", new String[]{until});
    }

    public long saveCustomer(long id, Map<String,String> m) {
        ContentValues v = cv(m, "name","contact","phone","email","address","notes");long saved=id;
        if (id == 0) { v.put("created_at", now()); saved=getWritableDatabase().insertOrThrow("customers", null, v); }
        else getWritableDatabase().update("customers", v, "id=?", new String[]{String.valueOf(id)});queueSync("customer",saved,"upsert");return saved;
    }
    public long saveSite(long id, Map<String,String> m) {
        ContentValues v = cv(m, "name","address","contact","phone","notes"); putLong(v,"customer_id",m.get("customer_id"));long saved=id;
        if (id==0){v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("sites",null,v);}else getWritableDatabase().update("sites",v,"id=?",new String[]{String.valueOf(id)});queueSync("site",saved,"upsert");return saved;
    }
    public long saveAsset(long id, Map<String,String> m) {
        ContentValues v=cv(m,"tag","name","category","make_model","serial","location","notes","next_service"); putLong(v,"customer_id",m.get("customer_id")); putLong(v,"site_id",m.get("site_id")); putInt(v,"interval_days",m.get("interval_days"));long saved=id;
        if(id==0){v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("assets",null,v);}else getWritableDatabase().update("assets",v,"id=?",new String[]{String.valueOf(id)});queueSync("asset",saved,"upsert");return saved;
    }
    public long saveJob(long id, Map<String,String> m, String prefix) {
        ContentValues v=cv(m,"title","problem","diagnosis","work_done","parts","technician","priority","status","job_date","next_service","customer_name_signed"); putLong(v,"customer_id",m.get("customer_id")); putLong(v,"site_id",m.get("site_id")); putLong(v,"asset_id",m.get("asset_id")); v.put("updated_at",now());long saved=id;
        if(id==0){v.put("report_no",nextReportNo(prefix));v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("jobs",null,v);}else getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(id)});queueSync("job",saved,"upsert");return saved;
    }

    private ContentValues cv(Map<String,String> m,String... keys){ContentValues v=new ContentValues();for(String k:keys)v.put(k,m.getOrDefault(k,""));return v;}
    private void putLong(ContentValues v,String k,String s){try{long x=Long.parseLong(s==null?"0":s);if(x>0)v.put(k,x);else v.putNull(k);}catch(Exception e){v.putNull(k);}}
    private void putInt(ContentValues v,String k,String s){try{v.put(k,Integer.parseInt(s==null?"0":s));}catch(Exception e){v.put(k,0);}}

    public synchronized String nextReportNo(String prefix) {
        SQLiteDatabase db=getWritableDatabase(); int y=Calendar.getInstance().get(Calendar.YEAR); int seq=1;
        db.beginTransaction();
        try {
            Cursor c=db.rawQuery("SELECT seq FROM sequences WHERE year=?",new String[]{String.valueOf(y)});
            try{if(c.moveToFirst())seq=c.getInt(0)+1;}finally{c.close();}
            ContentValues v=new ContentValues();v.put("year",y);v.put("seq",seq);db.insertWithOnConflict("sequences",null,v,SQLiteDatabase.CONFLICT_REPLACE);db.setTransactionSuccessful();
        } finally {db.endTransaction();}
        String p=(prefix==null||prefix.trim().isEmpty())?"FSR":prefix.trim().toUpperCase(Locale.US);
        return String.format(Locale.US,"%s-%d-%05d",p,y,seq);
    }

    public String nextAssetTag() { long n=count("assets",null,null)+1; return String.format(Locale.US,"AST-%05d",n); }


    public void setJobStatus(long jobId, String status) {
        ContentValues v=new ContentValues();v.put("status",status);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    public void deleteById(String table,long id){getWritableDatabase().delete(table,"id=?",new String[]{String.valueOf(id)});String type=table.endsWith("s")?table.substring(0,table.length()-1):table;queueSync(type,id,"delete");}

    public void addPhoto(long jobId,String uri){ContentValues v=new ContentValues();v.put("job_id",jobId);v.put("uri",uri);v.put("caption","");v.put("created_at",now());getWritableDatabase().insert("job_photos",null,v);queueSync("job",jobId,"upsert");}
    public List<Row> photos(long jobId){return rows("SELECT * FROM job_photos WHERE job_id=? ORDER BY id",new String[]{String.valueOf(jobId)});}
    public void setSignature(long jobId,String path,String signer){ContentValues v=new ContentValues();v.put("signature_path",path);v.put("customer_name_signed",signer);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");}

    public void completeMaintenance(long assetId,long jobId,String notes,String nextService){ContentValues v=new ContentValues();v.put("asset_id",assetId);if(jobId>0)v.put("job_id",jobId);v.put("service_date",today());v.put("notes",notes);v.put("next_service",nextService);v.put("created_at",now());getWritableDatabase().insert("maintenance_logs",null,v);if(nextService!=null&&!nextService.isEmpty()){ContentValues a=new ContentValues();a.put("next_service",nextService);getWritableDatabase().update("assets",a,"id=?",new String[]{String.valueOf(assetId)});}queueSync("asset",assetId,"upsert");if(jobId>0)queueSync("job",jobId,"upsert");}
    public void completeMaintenanceIfNeeded(long assetId,long jobId,String notes,String nextService){if(jobId>0&&count("maintenance_logs","job_id=?",new String[]{String.valueOf(jobId)})>0)return;completeMaintenance(assetId,jobId,notes,nextService);}

    public JSONObject exportJson() throws Exception {
        JSONObject root=new JSONObject();root.put("format","FidaFieldBackup");root.put("version",1);root.put("exported_at",now());
        String[] tables={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","sequences"};
        SQLiteDatabase db=getReadableDatabase();
        for(String table:tables){JSONArray arr=new JSONArray();Cursor c=db.rawQuery("SELECT * FROM "+table,null);try{while(c.moveToNext()){JSONObject o=new JSONObject();for(int i=0;i<c.getColumnCount();i++){if(c.isNull(i))o.put(c.getColumnName(i),JSONObject.NULL);else o.put(c.getColumnName(i),c.getString(i));}arr.put(o);}}finally{c.close();}root.put(table,arr);}return root;
    }

    public void importJson(JSONObject root) throws Exception {
        String[] tables={"maintenance_logs","job_photos","jobs","assets","sites","customers","technicians","sequences"}; SQLiteDatabase db=getWritableDatabase(); db.beginTransaction();
        try{for(String t:tables)db.delete(t,null,null);db.delete("sync_queue",null,null);String[] order={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","sequences"};for(String t:order){JSONArray arr=root.optJSONArray(t);if(arr==null)continue;for(int i=0;i<arr.length();i++){JSONObject o=arr.getJSONObject(i);ContentValues v=new ContentValues();java.util.Iterator<String> it=o.keys();while(it.hasNext()){String k=it.next();if(o.isNull(k))v.putNull(k);else v.put(k,o.getString(k));}db.insertOrThrow(t,null,v);}}String stamp=now();queueExistingForSync(db,"customer","customers",stamp);queueExistingForSync(db,"site","sites",stamp);queueExistingForSync(db,"asset","assets",stamp);queueExistingForSync(db,"job","jobs",stamp);queueExistingForSync(db,"technician","technicians",stamp);db.setTransactionSuccessful();}finally{db.endTransaction();}
    }

    public void insertDemoData() {
        if(count("customers",null,null)>0)return;
        long c1=saveCustomer(0,map("name","Kigali Business Center","contact","Alice","phone","+250 788 000 001","email","alice@example.com","address","Kigali","notes","Demo customer"));
        long s1=saveSite(0,map("customer_id",String.valueOf(c1),"name","Main Office","address","Kigali","contact","Eric","phone","+250 788 000 002","notes",""));
        saveAsset(0,map("customer_id",String.valueOf(c1),"site_id",String.valueOf(s1),"tag","AST-00001","name","Main UPS","category","UPS / Power","make_model","APC Smart-UPS","serial","DEMO-001","location","Server Room","notes","Quarterly inspection","interval_days","90","next_service",today()));
    }

    public static Map<String,String> map(String... kv){HashMap<String,String> m=new HashMap<>();for(int i=0;i+1<kv.length;i+=2)m.put(kv[i],kv[i+1]);return m;}
}
