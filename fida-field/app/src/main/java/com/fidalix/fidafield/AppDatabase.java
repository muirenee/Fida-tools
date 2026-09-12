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
import java.util.Set;

public class AppDatabase extends SQLiteOpenHelper {
    public static final String DB_NAME = "fida_field.db";
    public static final int DB_VERSION = 11;

    public static class Row extends HashMap<String, String> {
        public long id() { try { return Long.parseLong(getOrDefault("id", "0")); } catch (Exception e) { return 0; } }
        public String s(String k) { return getOrDefault(k, ""); }
        public int i(String k) { try { return Integer.parseInt(getOrDefault(k, "0")); } catch (Exception e) { return 0; } }
        public long l(String k) { try { return Long.parseLong(getOrDefault(k, "0")); } catch (Exception e) { return 0L; } }
    }

    public AppDatabase(Context context) { super(context, DB_NAME, null, DB_VERSION); }

    @Override public void onConfigure(SQLiteDatabase db) {
        super.onConfigure(db);
        db.setForeignKeyConstraintsEnabled(true);
    }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, contact TEXT, phone TEXT, email TEXT, address TEXT, notes TEXT, created_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE sites (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, name TEXT NOT NULL, address TEXT, contact TEXT, phone TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE)");
        db.execSQL("CREATE TABLE customer_sites (customer_id INTEGER NOT NULL, site_id INTEGER NOT NULL, PRIMARY KEY(customer_id,site_id), FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE)");
        db.execSQL("CREATE INDEX idx_customer_sites_customer ON customer_sites(customer_id,site_id)");
        db.execSQL("CREATE INDEX idx_customer_sites_site ON customer_sites(site_id,customer_id)");
        db.execSQL("CREATE TABLE assets (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, site_id INTEGER, tag TEXT NOT NULL UNIQUE, name TEXT NOT NULL, category TEXT, make_model TEXT, serial TEXT, location TEXT, notes TEXT, interval_days INTEGER DEFAULT 0, next_service TEXT, created_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE SET NULL)");
        db.execSQL("CREATE TABLE jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, report_no TEXT NOT NULL UNIQUE, customer_id INTEGER, site_id INTEGER, asset_id INTEGER, title TEXT NOT NULL, problem TEXT, diagnosis TEXT, work_done TEXT, parts TEXT, technician TEXT, technician_id INTEGER, priority TEXT DEFAULT 'Normal', status TEXT DEFAULT 'Open', job_date TEXT NOT NULL, next_service TEXT, service_started_at_ms INTEGER DEFAULT 0, service_completed_at_ms INTEGER DEFAULT 0, service_duration_minutes INTEGER DEFAULT 0, signature_path TEXT, customer_name_signed TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE SET NULL, FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE SET NULL)");
        db.execSQL("CREATE TABLE job_photos (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, uri TEXT NOT NULL, caption TEXT, created_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)");
        db.execSQL("CREATE TABLE maintenance_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id INTEGER NOT NULL, job_id INTEGER, service_date TEXT NOT NULL, notes TEXT, next_service TEXT, created_at TEXT NOT NULL, FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE SET NULL)");
        db.execSQL("CREATE TABLE technicians (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT, phone TEXT, email TEXT, user_uuid TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE job_assignment_history (id INTEGER PRIMARY KEY AUTOINCREMENT, remote_uuid TEXT UNIQUE, job_id INTEGER NOT NULL, from_technician_id INTEGER, to_technician_id INTEGER, from_technician_name TEXT, to_technician_name TEXT, changed_by TEXT, changed_at TEXT NOT NULL, pending INTEGER DEFAULT 0, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)");
        db.execSQL("CREATE INDEX idx_job_assignment_history_job ON job_assignment_history(job_id,changed_at)");
        db.execSQL("CREATE INDEX idx_jobs_technician_id ON jobs(technician_id)");
        db.execSQL("CREATE TABLE sequences (year INTEGER PRIMARY KEY, seq INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE sync_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, operation TEXT NOT NULL DEFAULT 'upsert', changed_at TEXT NOT NULL, UNIQUE(entity_type,entity_id))");
        db.execSQL("CREATE TABLE workspace_members (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, member_uuid TEXT NOT NULL UNIQUE, user_uuid TEXT, name TEXT NOT NULL, email TEXT, role TEXT NOT NULL DEFAULT 'Technician', status TEXT NOT NULL DEFAULT 'Active', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE workspace_invites (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, invite_uuid TEXT NOT NULL UNIQUE, email TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Technician', status TEXT NOT NULL DEFAULT 'Pending', token TEXT, expires_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)");
        db.execSQL("CREATE TABLE sync_metadata (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, remote_uuid TEXT NOT NULL UNIQUE, server_version INTEGER DEFAULT 0, last_synced_at TEXT, deleted_at TEXT, UNIQUE(entity_type,entity_id))");
        db.execSQL("CREATE TABLE sync_conflicts (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, remote_uuid TEXT, reason TEXT NOT NULL, detected_at TEXT NOT NULL, UNIQUE(entity_type,entity_id))");
        db.execSQL("CREATE INDEX idx_sync_conflicts_detected ON sync_conflicts(detected_at DESC)");
        db.execSQL("CREATE INDEX idx_workspace_members_workspace ON workspace_members(workspace_id,status)");
        db.execSQL("CREATE INDEX idx_workspace_invites_workspace ON workspace_invites(workspace_id,status)");
        db.execSQL("CREATE INDEX idx_technicians_user_uuid ON technicians(user_uuid)");
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
        if(oldVersion<5){
            db.execSQL("ALTER TABLE workspace_members ADD COLUMN user_uuid TEXT");
            db.execSQL("ALTER TABLE workspace_invites ADD COLUMN token TEXT");
            db.execSQL("ALTER TABLE workspace_invites ADD COLUMN expires_at TEXT");
        }
        if(oldVersion<6){
            String stamp=now();
            queueExistingForSync(db,"job_photo","job_photos",stamp);
            queueExistingForSync(db,"maintenance_log","maintenance_logs",stamp);
            db.execSQL("INSERT OR REPLACE INTO sync_queue(entity_type,entity_id,operation,changed_at) SELECT 'job_signature',id,'upsert',? FROM jobs WHERE signature_path IS NOT NULL AND signature_path<>''",new Object[]{stamp});
        }
        if(oldVersion<7){
            db.execSQL("CREATE TABLE IF NOT EXISTS sync_conflicts (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, remote_uuid TEXT, reason TEXT NOT NULL, detected_at TEXT NOT NULL, UNIQUE(entity_type,entity_id))");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_sync_conflicts_detected ON sync_conflicts(detected_at DESC)");
        }
        if(oldVersion<8){
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
        if(oldVersion<10){
            db.execSQL("CREATE TABLE IF NOT EXISTS customer_sites (customer_id INTEGER NOT NULL, site_id INTEGER NOT NULL, PRIMARY KEY(customer_id,site_id), FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE)");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_customer ON customer_sites(customer_id,site_id)");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_site ON customer_sites(site_id,customer_id)");
            db.execSQL("INSERT OR IGNORE INTO customer_sites(customer_id,site_id) SELECT customer_id,id FROM sites WHERE customer_id IS NOT NULL");
        }
        if(oldVersion<11){
            db.execSQL("ALTER TABLE jobs ADD COLUMN service_started_at_ms INTEGER DEFAULT 0");
            db.execSQL("ALTER TABLE jobs ADD COLUMN service_completed_at_ms INTEGER DEFAULT 0");
            db.execSQL("ALTER TABLE jobs ADD COLUMN service_duration_minutes INTEGER DEFAULT 0");
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
    public int clearCancelledWorkspaceInvites(String workspaceId){return getWritableDatabase().delete("workspace_invites","workspace_id=? AND status=\'Cancelled\'",new String[]{workspaceId==null?"":workspaceId});}
    public String ensureRemoteUuid(String type,long entityId){Row r=one("SELECT remote_uuid FROM sync_metadata WHERE entity_type=? AND entity_id=?",new String[]{type,String.valueOf(entityId)});if(!r.s("remote_uuid").isEmpty())return r.s("remote_uuid");String uuid=java.util.UUID.randomUUID().toString();ContentValues v=new ContentValues();v.put("entity_type",type);v.put("entity_id",entityId);v.put("remote_uuid",uuid);getWritableDatabase().insertWithOnConflict("sync_metadata",null,v,SQLiteDatabase.CONFLICT_IGNORE);return one("SELECT remote_uuid FROM sync_metadata WHERE entity_type=? AND entity_id=?",new String[]{type,String.valueOf(entityId)}).s("remote_uuid");}
    public List<Row> pendingSyncRows(){return rows("SELECT q.*,m.remote_uuid,m.server_version,m.last_synced_at FROM sync_queue q LEFT JOIN sync_metadata m ON m.entity_type=q.entity_type AND m.entity_id=q.entity_id ORDER BY q.changed_at,q.id",null);}

    public long pendingBusinessChanges(){return count("sync_queue","entity_type IN ('customer','site','customer_site','asset','technician','job','job_photo','maintenance_log','job_signature')",null);}
    public List<Row> pendingBusinessSyncRows(){return rows("SELECT q.*,m.remote_uuid,m.server_version,m.last_synced_at FROM sync_queue q LEFT JOIN sync_metadata m ON m.entity_type=q.entity_type AND m.entity_id=q.entity_id WHERE q.entity_type IN ('customer','site','asset','technician','job') ORDER BY q.changed_at,q.id",null);}
    public void discardManagerOnlyPendingChanges(){getWritableDatabase().delete("sync_queue","entity_type IN ('customer','site','customer_site','asset','technician')",null);getWritableDatabase().delete("sync_conflicts","entity_type IN ('customer','site','asset','technician')",null);}
    public Row syncEntity(String type,long id){if("customer".equals(type))return getCustomer(id);if("site".equals(type))return getSite(id);if("asset".equals(type))return getAsset(id);if("technician".equals(type))return getTechnician(id);if("job".equals(type))return one("SELECT * FROM jobs WHERE id=?",new String[]{String.valueOf(id)});return new Row();}
    public long localIdForRemote(String type,String remoteUuid){if(remoteUuid==null||remoteUuid.isEmpty())return 0;Row r=one("SELECT entity_id FROM sync_metadata WHERE entity_type=? AND remote_uuid=?",new String[]{type,remoteUuid});try{return Long.parseLong(r.s("entity_id"));}catch(Exception e){return 0;}}
    public void bindRemoteUuid(String type,long localId,String remoteUuid){if(localId<=0||remoteUuid==null||remoteUuid.isEmpty())return;Row old=one("SELECT id FROM sync_metadata WHERE entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)});ContentValues v=new ContentValues();v.put("remote_uuid",remoteUuid);v.put("last_synced_at",now());if(old.id()>0)getWritableDatabase().update("sync_metadata",v,"id=?",new String[]{String.valueOf(old.id())});else{v.put("entity_type",type);v.put("entity_id",localId);getWritableDatabase().insertOrThrow("sync_metadata",null,v);}}
    public void markEntitySynced(String type,long localId,String remoteUuid){bindRemoteUuid(type,localId,remoteUuid);getWritableDatabase().delete("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)});resolveSyncConflict(type,localId);}
    public boolean hasEverSynced(String type,long localId){return localId>0&&count("sync_metadata","entity_type=? AND entity_id=? AND last_synced_at IS NOT NULL AND trim(last_synced_at)<>''",new String[]{type,String.valueOf(localId)})>0;}
    public long maxLocalReportSequence(String reportNo){
        if(reportNo==null)return 0;String value=reportNo.trim().toUpperCase(Locale.US);int last=value.lastIndexOf('-');if(last<1||last>=value.length()-1)return 0;String stem=value.substring(0,last+1);long max=0;
        for(Row r:rows("SELECT report_no FROM jobs WHERE upper(report_no) LIKE ?",new String[]{stem+"%"})){String n=r.s("report_no").trim().toUpperCase(Locale.US);if(!n.startsWith(stem))continue;try{max=Math.max(max,Long.parseLong(n.substring(stem.length())));}catch(Exception ignored){}}return max;
    }
    public void updateJobReportNoFromCloud(long jobId,String reportNo){if(jobId<=0||reportNo==null||reportNo.trim().isEmpty())return;ContentValues v=new ContentValues();v.put("report_no",reportNo.trim().toUpperCase(Locale.US));v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});}
    public boolean hasPendingSync(String type,long localId){return localId>0&&count("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)})>0;}
    public long unresolvedConflictCount(){return count("sync_conflicts",null,null);}
    public List<Row> recentSyncConflicts(int limit){return rows("SELECT * FROM sync_conflicts ORDER BY detected_at DESC,id DESC LIMIT "+Math.max(1,Math.min(50,limit)),null);}
    public void recordSyncConflict(String type,long localId,String remoteUuid,String reason){if(localId<=0)return;ContentValues v=new ContentValues();v.put("entity_type",type);v.put("entity_id",localId);v.put("remote_uuid",remoteUuid==null?"":remoteUuid);v.put("reason",reason==null?"Cloud change deferred":reason);v.put("detected_at",now());getWritableDatabase().insertWithOnConflict("sync_conflicts",null,v,SQLiteDatabase.CONFLICT_REPLACE);}
    public void resolveSyncConflict(String type,long localId){getWritableDatabase().delete("sync_conflicts","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)});}
    public void markDeletionSynced(String type,long localId,String remoteUuid){SQLiteDatabase d=getWritableDatabase();ContentValues v=new ContentValues();v.put("deleted_at",now());v.put("last_synced_at",now());Row m=one("SELECT id FROM sync_metadata WHERE entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)});if(m.id()>0)d.update("sync_metadata",v,"id=?",new String[]{String.valueOf(m.id())});else if(remoteUuid!=null&&!remoteUuid.isEmpty()){v.put("entity_type",type);v.put("entity_id",localId);v.put("remote_uuid",remoteUuid);d.insertWithOnConflict("sync_metadata",null,v,SQLiteDatabase.CONFLICT_IGNORE);}d.delete("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)});resolveSyncConflict(type,localId);}
    private String localTableForType(String type){if("customer".equals(type))return "customers";if("site".equals(type))return "sites";if("asset".equals(type))return "assets";if("technician".equals(type))return "technicians";if("job".equals(type))return "jobs";if("job_photo".equals(type))return "job_photos";if("maintenance_log".equals(type))return "maintenance_logs";return "";}
    public boolean hasPendingDependents(String type,long localId){if(localId<=0)return false;if("customer".equals(type))return count("sync_queue","entity_type='site' AND entity_id IN (SELECT id FROM sites WHERE customer_id=?)",new String[]{String.valueOf(localId)})>0;if("asset".equals(type))return count("sync_queue","entity_type='maintenance_log' AND entity_id IN (SELECT id FROM maintenance_logs WHERE asset_id=?)",new String[]{String.valueOf(localId)})>0;if("job".equals(type))return count("sync_queue","(entity_type='job_photo' AND entity_id IN (SELECT id FROM job_photos WHERE job_id=?)) OR (entity_type='job_signature' AND entity_id=?)",new String[]{String.valueOf(localId),String.valueOf(localId)})>0;return false;}
    public boolean applyRemoteDeletion(String type,String remoteUuid){long local=localIdForRemote(type,remoteUuid);if(local<=0)return false;if(hasPendingSync(type,local)||hasPendingDependents(type,local)){recordSyncConflict(type,local,remoteUuid,"Cloud deletion deferred because this device has unsynced work");return false;}String table=localTableForType(type);if(table.isEmpty())return false;SQLiteDatabase d=getWritableDatabase();if("customer".equals(type))rehomeSharedSitesBeforeCustomerDelete(local,false);d.delete(table,"id=?",new String[]{String.valueOf(local)});markDeletionSynced(type,local,remoteUuid);return true;}
    public void rebindWorkspace(String oldId,String newId){if(oldId==null||newId==null||oldId.isEmpty()||newId.isEmpty()||oldId.equals(newId))return;ContentValues v=new ContentValues();v.put("workspace_id",newId);getWritableDatabase().update("workspace_members",v,"workspace_id=?",new String[]{oldId});getWritableDatabase().update("workspace_invites",v,"workspace_id=?",new String[]{oldId});}
    public void cacheWorkspaceTeam(String workspaceId,JSONArray members,JSONArray invites)throws Exception{
        SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{d.delete("workspace_members","workspace_id=?",new String[]{workspaceId});d.delete("workspace_invites","workspace_id=?",new String[]{workspaceId});
            for(int i=0;i<members.length();i++){JSONObject o=members.getJSONObject(i);ContentValues v=new ContentValues();v.put("workspace_id",workspaceId);v.put("member_uuid",o.optString("member_id",java.util.UUID.randomUUID().toString()));v.put("user_uuid",o.optString("user_id",""));String name=o.optString("full_name","");String email=o.optString("email","");v.put("name",name.isEmpty()?(email.isEmpty()?"Team member":email):name);v.put("email",email);v.put("role",AccountTeamManager.normalizeRole(o.optString("role","technician")));v.put("status",AccountTeamManager.normalizeStatus(o.optString("status","active")));v.put("created_at",now());v.put("updated_at",now());d.insertOrThrow("workspace_members",null,v);}
            for(int i=0;i<invites.length();i++){JSONObject o=invites.getJSONObject(i);ContentValues v=new ContentValues();v.put("workspace_id",workspaceId);v.put("invite_uuid",o.optString("invite_id",java.util.UUID.randomUUID().toString()));v.put("email",o.optString("email",""));v.put("role",AccountTeamManager.normalizeRole(o.optString("role","technician")));v.put("status",AccountTeamManager.normalizeStatus(o.optString("status","pending")));v.put("token",o.optString("token",""));v.put("expires_at",o.optString("expires_at",""));v.put("created_at",now());v.put("updated_at",now());d.insertOrThrow("workspace_invites",null,v);}
            d.delete("sync_queue","entity_type IN ('workspace_member','workspace_invite')",null);d.setTransactionSuccessful();}finally{d.endTransaction();}
        autoLinkPeople(workspaceId);
    }
    private String j(JSONObject o,String k){return o==null||o.isNull(k)?"":o.optString(k,"");}
    private void jt(ContentValues v,JSONObject o,String... keys){for(String k:keys)v.put(k,j(o,k));}
    private long remoteLocal(String type,JSONObject o,String key){String u=j(o,key);return u.isEmpty()?0:localIdForRemote(type,u);}
    public long upsertRemoteEntity(String type,JSONObject o)throws Exception{
        String remote=j(o,"id");if(remote.isEmpty())return 0;long local=localIdForRemote(type,remote);SQLiteDatabase d=getWritableDatabase();ContentValues v=new ContentValues();
        if(local>0&&hasPendingSync(type,local)){recordSyncConflict(type,local,remote,"Cloud update deferred because this device has unsynced edits");return local;}
        if("customer".equals(type)){jt(v,o,"name","contact","phone","email","address","notes");if(local==0){v.put("created_at",now());local=d.insertOrThrow("customers",null,v);}else d.update("customers",v,"id=?",new String[]{String.valueOf(local)});}
        else if("site".equals(type)){long cid=remoteLocal("customer",o,"customer_id");if(cid<=0)return 0;jt(v,o,"name","address","contact","phone","notes");v.put("customer_id",cid);if(local==0){v.put("created_at",now());local=d.insertOrThrow("sites",null,v);}else d.update("sites",v,"id=?",new String[]{String.valueOf(local)});}
        else if("asset".equals(type)){if(local==0&&!j(o,"tag").isEmpty())local=getAssetByTag(j(o,"tag")).id();if(local>0&&hasPendingSync(type,local)){recordSyncConflict(type,local,remote,"Cloud update deferred because this device has unsynced edits");return local;}jt(v,o,"tag","name","category","make_model","serial","location","notes","next_service");long cid=remoteLocal("customer",o,"customer_id"),sid=remoteLocal("site",o,"site_id");if(cid>0)v.put("customer_id",cid);else v.putNull("customer_id");if(sid>0)v.put("site_id",sid);else v.putNull("site_id");v.put("interval_days",o.optInt("interval_days",0));if(local==0){v.put("created_at",now());local=d.insertOrThrow("assets",null,v);}else d.update("assets",v,"id=?",new String[]{String.valueOf(local)});}
        else if("technician".equals(type)){String linkedUser=j(o,"user_id");if(local==0&&!linkedUser.isEmpty())local=technicianForUser(linkedUser).id();jt(v,o,"name","role","phone","email");if(linkedUser.isEmpty())v.putNull("user_uuid");else v.put("user_uuid",linkedUser);v.put("active",o.optBoolean("active",true)?1:0);if(local==0){v.put("created_at",now());local=d.insertOrThrow("technicians",null,v);}else d.update("technicians",v,"id=?",new String[]{String.valueOf(local)});}
        else if("job".equals(type)){if(local==0&&!j(o,"report_no").isEmpty())local=one("SELECT * FROM jobs WHERE report_no=?",new String[]{j(o,"report_no")}).id();if(local>0&&hasPendingSync(type,local)){recordSyncConflict(type,local,remote,"Cloud update deferred because this device has unsynced edits");return local;}jt(v,o,"report_no","title","problem","diagnosis","work_done","parts","priority","status","job_date","next_service","customer_name_signed");v.put("service_started_at_ms",o.optLong("service_started_at_ms",0L));v.put("service_completed_at_ms",o.optLong("service_completed_at_ms",0L));v.put("service_duration_minutes",o.optInt("service_duration_minutes",0));v.put("technician",j(o,"technician_name"));long tid=remoteLocal("technician",o,"technician_id");if(tid>0)v.put("technician_id",tid);else v.putNull("technician_id");long cid=remoteLocal("customer",o,"customer_id"),sid=remoteLocal("site",o,"site_id"),aid=remoteLocal("asset",o,"asset_id");if(cid>0)v.put("customer_id",cid);else v.putNull("customer_id");if(sid>0)v.put("site_id",sid);else v.putNull("site_id");if(aid>0)v.put("asset_id",aid);else v.putNull("asset_id");v.put("updated_at",now());if(local==0){v.put("created_at",now());local=d.insertOrThrow("jobs",null,v);}else d.update("jobs",v,"id=?",new String[]{String.valueOf(local)});}
        else return 0;bindRemoteUuid(type,local,remote);d.delete("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(local)});resolveSyncConflict(type,local);return local;
    }

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
    public Row technicianForUser(String userUuid){if(userUuid==null||userUuid.trim().isEmpty())return new Row();return one("SELECT * FROM technicians WHERE user_uuid=? LIMIT 1",new String[]{userUuid.trim()});}
    public Row workspaceMemberForUser(String workspaceId,String userUuid){if(workspaceId==null||workspaceId.isEmpty()||userUuid==null||userUuid.isEmpty())return new Row();return one("SELECT * FROM workspace_members WHERE workspace_id=? AND user_uuid=? LIMIT 1",new String[]{workspaceId,userUuid});}
    public List<Row> unlinkedWorkspaceMembers(String workspaceId){return rows("SELECT m.* FROM workspace_members m WHERE m.workspace_id=? AND m.status='Active' AND m.user_uuid IS NOT NULL AND m.user_uuid<>'' AND NOT EXISTS (SELECT 1 FROM technicians t WHERE t.user_uuid=m.user_uuid) ORDER BY CASE m.role WHEN 'Owner' THEN 0 WHEN 'Admin' THEN 1 WHEN 'Technician' THEN 2 ELSE 3 END,m.name COLLATE NOCASE",new String[]{workspaceId==null?"":workspaceId});}
    public long saveTechnician(long id, Map<String,String> m) {
        ContentValues v=cv(m,"name","role","phone","email");if(m.containsKey("user_uuid")){String u=m.get("user_uuid");if(u==null||u.trim().isEmpty())v.putNull("user_uuid");else v.put("user_uuid",u.trim());}putInt(v,"active",m.get("active"));long saved=id;
        if(id==0){v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("technicians",null,v);}else getWritableDatabase().update("technicians",v,"id=?",new String[]{String.valueOf(id)});queueSync("technician",saved,"upsert");return saved;
    }
    public void deletePersonTechnician(long technicianId){
        if(technicianId<=0)return;Row tech=getTechnician(technicianId);if(tech.id()==0)return;SQLiteDatabase d=getWritableDatabase();d.beginTransaction();
        try{
            for(Row j:rows("SELECT id FROM jobs WHERE technician_id=?",new String[]{String.valueOf(technicianId)})){ContentValues v=new ContentValues();v.putNull("technician_id");d.update("jobs",v,"id=?",new String[]{String.valueOf(j.id())});queueSync("job",j.id(),"upsert");}
            ContentValues from=new ContentValues();from.putNull("from_technician_id");d.update("job_assignment_history",from,"from_technician_id=?",new String[]{String.valueOf(technicianId)});ContentValues to=new ContentValues();to.putNull("to_technician_id");d.update("job_assignment_history",to,"to_technician_id=?",new String[]{String.valueOf(technicianId)});
            queueSync("technician",technicianId,"delete");d.delete("sync_conflicts","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(technicianId)});d.delete("technicians","id=?",new String[]{String.valueOf(technicianId)});d.setTransactionSuccessful();
        }finally{d.endTransaction();}
    }
    public void deleteWorkspaceMemberLocal(long memberId){if(memberId<=0)return;getWritableDatabase().delete("workspace_members","id=?",new String[]{String.valueOf(memberId)});}

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
    public long reconcileTechnicianIdentity(long sourceId,long targetId,String remoteUuid){
        if(sourceId<=0)return targetId;if(targetId<=0||sourceId==targetId){bindRemoteUuid("technician",sourceId,remoteUuid);return sourceId;}
        Row src=getTechnician(sourceId),target=getTechnician(targetId);if(src.id()==0){bindRemoteUuid("technician",targetId,remoteUuid);return targetId;}if(target.id()==0){bindRemoteUuid("technician",sourceId,remoteUuid);return sourceId;}
        SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{
            ContentValues v=new ContentValues();v.put("name",src.s("name"));v.put("role",src.s("role"));v.put("phone",src.s("phone"));v.put("email",src.s("email"));String user=src.s("user_uuid");if(user.isEmpty())v.putNull("user_uuid");else v.put("user_uuid",user);v.put("active",src.i("active"));d.update("technicians",v,"id=?",new String[]{String.valueOf(targetId)});
            ContentValues jv=new ContentValues();jv.put("technician_id",targetId);jv.put("technician",src.s("name"));d.update("jobs",jv,"technician_id=?",new String[]{String.valueOf(sourceId)});
            ContentValues fv=new ContentValues();fv.put("from_technician_id",targetId);d.update("job_assignment_history",fv,"from_technician_id=?",new String[]{String.valueOf(sourceId)});ContentValues tv=new ContentValues();tv.put("to_technician_id",targetId);d.update("job_assignment_history",tv,"to_technician_id=?",new String[]{String.valueOf(sourceId)});
            d.delete("sync_queue","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(sourceId)});d.delete("sync_conflicts","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(sourceId)});d.delete("sync_metadata","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(sourceId)});d.delete("technicians","id=?",new String[]{String.valueOf(sourceId)});
            Row meta=one("SELECT id FROM sync_metadata WHERE entity_type='technician' AND entity_id=?",new String[]{String.valueOf(targetId)});ContentValues mv=new ContentValues();mv.put("remote_uuid",remoteUuid);if(meta.id()>0)d.update("sync_metadata",mv,"id=?",new String[]{String.valueOf(meta.id())});else{mv.put("entity_type","technician");mv.put("entity_id",targetId);d.insertOrThrow("sync_metadata",null,mv);}
            ContentValues qv=new ContentValues();qv.put("entity_type","technician");qv.put("entity_id",targetId);qv.put("operation","upsert");qv.put("changed_at",now());d.insertWithOnConflict("sync_queue",null,qv,SQLiteDatabase.CONFLICT_REPLACE);
            d.setTransactionSuccessful();
        }finally{d.endTransaction();}
        return targetId;
    }

    public List<Row> jobsForAsset(long assetId){return rows("SELECT j.*,c.name customer_name FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id WHERE j.asset_id=? ORDER BY j.job_date DESC,j.id DESC",new String[]{String.valueOf(assetId)});}
    public List<Row> maintenanceForAsset(long assetId){return rows("SELECT m.*,j.report_no,j.title job_title FROM maintenance_logs m LEFT JOIN jobs j ON j.id=m.job_id WHERE m.asset_id=? ORDER BY m.service_date DESC,m.id DESC",new String[]{String.valueOf(assetId)});}
    public String suggestNextService(long assetId,String fromDate){Row a=getAsset(assetId);int days=a.i("interval_days");if(days<=0)return "";try{SimpleDateFormat f=new SimpleDateFormat("yyyy-MM-dd",Locale.US);Date d=f.parse(fromDate==null||fromDate.isEmpty()?today():fromDate);Calendar c=Calendar.getInstance();c.setTime(d==null?new Date():d);c.add(Calendar.DAY_OF_YEAR,days);return f.format(c.getTime());}catch(Exception e){return "";}}

    public Row getJob(long id) {
        return one("SELECT j.*, c.name customer_name, c.contact customer_contact, c.phone customer_phone, c.email customer_email, c.address customer_address, s.name site_name, s.contact site_contact, s.phone site_phone, s.address site_address, a.name asset_name, a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.id=?", new String[]{String.valueOf(id)});
    }

    public List<Row> customers() { return rows("SELECT * FROM customers ORDER BY name COLLATE NOCASE", null); }
    public List<Row> sites(long customerId) {
        String where=customerId>0?"WHERE EXISTS (SELECT 1 FROM customer_sites x WHERE x.site_id=s.id AND x.customer_id=?) ":"";
        return rows("SELECT s.*, group_concat(DISTINCT c.name) customer_name FROM sites s LEFT JOIN customer_sites cs ON cs.site_id=s.id LEFT JOIN customers c ON c.id=cs.customer_id "+where+"GROUP BY s.id ORDER BY s.name COLLATE NOCASE",customerId>0?new String[]{String.valueOf(customerId)}:null);
    }
    public long siteCountForCustomer(long customerId){return countSql("SELECT COUNT(*) FROM customer_sites WHERE customer_id=?",new String[]{String.valueOf(customerId)});}
    public boolean siteBelongsToCustomer(long siteId,long customerId){return siteId>0&&customerId>0&&count("customer_sites","site_id=? AND customer_id=?",new String[]{String.valueOf(siteId),String.valueOf(customerId)})>0;}
    public List<Long> customerIdsForSite(long siteId){ArrayList<Long> out=new ArrayList<>();for(Row r:rows("SELECT customer_id FROM customer_sites WHERE site_id=? ORDER BY customer_id",new String[]{String.valueOf(siteId)})){try{out.add(Long.parseLong(r.s("customer_id")));}catch(Exception ignored){}}return out;}
    public long firstCustomerIdForSite(long siteId){Row r=one("SELECT customer_id FROM customer_sites WHERE site_id=? ORDER BY customer_id LIMIT 1",new String[]{String.valueOf(siteId)});try{return Long.parseLong(r.s("customer_id"));}catch(Exception e){return 0;}}
    public String customerNamesForSite(long siteId){return one("SELECT group_concat(name, ', ') names FROM (SELECT c.name name FROM customer_sites cs JOIN customers c ON c.id=cs.customer_id WHERE cs.site_id=? ORDER BY c.name COLLATE NOCASE)",new String[]{String.valueOf(siteId)}).s("names");}
    public List<Row> customerSiteLinks(){return rows("SELECT customer_id,site_id FROM customer_sites ORDER BY site_id,customer_id",null);}
    public boolean hasCustomerSiteLinkChanges(){return count("sync_queue","entity_type='customer_site'",null)>0;}
    public void markCustomerSiteLinksSynced(){getWritableDatabase().delete("sync_queue","entity_type='customer_site'",null);}
    public void setSiteCustomers(long siteId,List<Long> customerIds){
        if(siteId<=0||customerIds==null||customerIds.isEmpty())return;SQLiteDatabase d=getWritableDatabase();d.beginTransaction();long first=0;
        try{d.delete("customer_sites","site_id=?",new String[]{String.valueOf(siteId)});for(Long cid:customerIds){if(cid==null||cid<=0)continue;if(first==0)first=cid;ContentValues v=new ContentValues();v.put("customer_id",cid);v.put("site_id",siteId);d.insertWithOnConflict("customer_sites",null,v,SQLiteDatabase.CONFLICT_IGNORE);}if(first>0){ContentValues sv=new ContentValues();sv.put("customer_id",first);d.update("sites",sv,"id=?",new String[]{String.valueOf(siteId)});}d.setTransactionSuccessful();}finally{d.endTransaction();}
        queueSync("site",siteId,"upsert");queueSync("customer_site",siteId,"upsert");
    }
    public void addSiteCustomers(long siteId,List<Long> customerIds){
        if(siteId<=0||customerIds==null||customerIds.isEmpty())return;SQLiteDatabase d=getWritableDatabase();long first=firstCustomerIdForSite(siteId);d.beginTransaction();try{for(Long cid:customerIds){if(cid==null||cid<=0)continue;ContentValues v=new ContentValues();v.put("customer_id",cid);v.put("site_id",siteId);d.insertWithOnConflict("customer_sites",null,v,SQLiteDatabase.CONFLICT_IGNORE);if(first==0)first=cid;}if(first>0){ContentValues sv=new ContentValues();sv.put("customer_id",first);d.update("sites",sv,"id=?",new String[]{String.valueOf(siteId)});}d.setTransactionSuccessful();}finally{d.endTransaction();}queueSync("site",siteId,"upsert");queueSync("customer_site",siteId,"upsert");
    }
    public void replaceCustomerSiteLinksFromCloud(JSONArray links)throws Exception{
        SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{d.delete("customer_sites",null,null);for(int i=0;i<links.length();i++){JSONObject o=links.getJSONObject(i);long cid=localIdForRemote("customer",o.optString("customer_id","")),sid=localIdForRemote("site",o.optString("site_id",""));if(cid<=0||sid<=0)continue;ContentValues v=new ContentValues();v.put("customer_id",cid);v.put("site_id",sid);d.insertWithOnConflict("customer_sites",null,v,SQLiteDatabase.CONFLICT_IGNORE);}d.setTransactionSuccessful();}finally{d.endTransaction();}
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
        Row before=id>0?one("SELECT technician_id,technician FROM jobs WHERE id=?",new String[]{String.valueOf(id)}):new Row();long oldTech=before.i("technician_id");
        ContentValues v=cv(m,"title","problem","diagnosis","work_done","parts","technician","priority","status","job_date","next_service","customer_name_signed"); putLong(v,"customer_id",m.get("customer_id")); putLong(v,"site_id",m.get("site_id")); putLong(v,"asset_id",m.get("asset_id")); putLong(v,"technician_id",m.get("technician_id")); v.put("updated_at",now());long saved=id;
        if(id==0){
            v.put("created_at",now());android.database.sqlite.SQLiteConstraintException last=null;
            for(int attempt=0;attempt<8;attempt++){
                v.put("report_no",nextReportNo(prefix));
                try{saved=getWritableDatabase().insertOrThrow("jobs",null,v);last=null;break;}
                catch(android.database.sqlite.SQLiteConstraintException e){last=e;}
            }
            if(saved<=0&&last!=null)throw last;
        }else getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(id)});long newTech=0;try{newTech=Long.parseLong(m.getOrDefault("technician_id","0"));}catch(Exception ignored){}if(saved>0&&oldTech!=newTech)recordLocalAssignment(saved,oldTech,newTech,m.getOrDefault("assignment_actor","Local user"));queueSync("job",saved,"upsert");return saved;
    }

    private ContentValues cv(Map<String,String> m,String... keys){ContentValues v=new ContentValues();for(String k:keys)v.put(k,m.getOrDefault(k,""));return v;}
    private void putLong(ContentValues v,String k,String s){try{long x=Long.parseLong(s==null?"0":s);if(x>0)v.put(k,x);else v.putNull(k);}catch(Exception e){v.putNull(k);}}
    private void putInt(ContentValues v,String k,String s){try{v.put(k,Integer.parseInt(s==null?"0":s));}catch(Exception e){v.put(k,0);}}

    public synchronized String nextReportNo(String prefix) {
        String p=(prefix==null||prefix.trim().isEmpty())?"FSR":prefix.trim().toUpperCase(Locale.US);
        int y=Calendar.getInstance().get(Calendar.YEAR);String stem=p+"-"+y+"-";SQLiteDatabase db=getWritableDatabase();int seq=0;String candidate;
        db.beginTransaction();
        try {
            Cursor c=db.rawQuery("SELECT seq FROM sequences WHERE year=?",new String[]{String.valueOf(y)});
            try{if(c.moveToFirst())seq=Math.max(seq,c.getInt(0));}finally{c.close();}
            Cursor jobs=db.rawQuery("SELECT report_no FROM jobs WHERE report_no LIKE ?",new String[]{stem+"%"});
            try{while(jobs.moveToNext()){String report=jobs.getString(0);if(report==null||!report.startsWith(stem))continue;try{seq=Math.max(seq,Integer.parseInt(report.substring(stem.length())));}catch(Exception ignored){}}}finally{jobs.close();}
            do{seq++;candidate=String.format(Locale.US,"%s%05d",stem,seq);}while(countSql("SELECT COUNT(*) FROM jobs WHERE report_no=?",new String[]{candidate})>0);
            ContentValues v=new ContentValues();v.put("year",y);v.put("seq",seq);db.insertWithOnConflict("sequences",null,v,SQLiteDatabase.CONFLICT_REPLACE);db.setTransactionSuccessful();
            return candidate;
        } finally {db.endTransaction();}
    }

    public String nextAssetTag() { long n=count("assets",null,null)+1; return String.format(Locale.US,"AST-%05d",n); }


    public void setJobStatus(long jobId, String status) {
        ContentValues v=new ContentValues();v.put("status",status);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    public void startJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0||"Completed".equalsIgnoreCase(job.s("status")))return;ContentValues v=new ContentValues();if(job.l("service_started_at_ms")<=0)v.put("service_started_at_ms",System.currentTimeMillis());if("Open".equalsIgnoreCase(job.s("status")))v.put("status","In Progress");v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    public void completeJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0)return;long started=job.l("service_started_at_ms"),finished=job.l("service_completed_at_ms");if(finished<=0)finished=System.currentTimeMillis();int minutes=0;if(started>0&&finished>=started)minutes=(int)Math.max(0L,Math.round((finished-started)/60000.0));ContentValues v=new ContentValues();v.put("service_completed_at_ms",finished);v.put("service_duration_minutes",minutes);v.put("status","Completed");v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    private void rehomeSharedSitesBeforeCustomerDelete(long customerId,boolean queueChanges){
        for(Row link:rows("SELECT site_id FROM customer_sites WHERE customer_id=?",new String[]{String.valueOf(customerId)})){long siteId=link.i("site_id");Row replacement=one("SELECT customer_id FROM customer_sites WHERE site_id=? AND customer_id<>? ORDER BY customer_id LIMIT 1",new String[]{String.valueOf(siteId),String.valueOf(customerId)});long next=replacement.i("customer_id");if(next>0){ContentValues v=new ContentValues();v.put("customer_id",next);getWritableDatabase().update("sites",v,"id=?",new String[]{String.valueOf(siteId)});if(queueChanges)queueSync("site",siteId,"upsert");}else if(queueChanges)queueSync("site",siteId,"delete");if(queueChanges)queueSync("customer_site",siteId,"upsert");}
    }
    public void deleteById(String table,long id){
        if(id<=0)return;
        if("customers".equals(table))rehomeSharedSitesBeforeCustomerDelete(id,true);
        else if("sites".equals(table))queueSync("customer_site",id,"upsert");
        else if("assets".equals(table)){for(Row r:rows("SELECT id FROM maintenance_logs WHERE asset_id=?",new String[]{String.valueOf(id)}))queueSync("maintenance_log",r.id(),"delete");}
        else if("jobs".equals(table)){for(Row r:photos(id))queueSync("job_photo",r.id(),"delete");queueSync("job_signature",id,"delete");}
        String type=table.endsWith("s")?table.substring(0,table.length()-1):table;queueSync(type,id,"delete");getWritableDatabase().delete(table,"id=?",new String[]{String.valueOf(id)});
    }

    public void addPhoto(long jobId,String uri){ContentValues v=new ContentValues();v.put("job_id",jobId);v.put("uri",uri);v.put("caption","");v.put("created_at",now());long saved=getWritableDatabase().insert("job_photos",null,v);queueSync("job_photo",saved,"upsert");queueSync("job",jobId,"upsert");}
    public List<Row> photos(long jobId){return rows("SELECT * FROM job_photos WHERE job_id=? ORDER BY id",new String[]{String.valueOf(jobId)});}
    public void setSignature(long jobId,String path,String signer){ContentValues v=new ContentValues();v.put("signature_path",path);v.put("customer_name_signed",signer);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");queueSync("job_signature",jobId,"upsert");}

    public void completeMaintenance(long assetId,long jobId,String notes,String nextService){ContentValues v=new ContentValues();v.put("asset_id",assetId);if(jobId>0)v.put("job_id",jobId);v.put("service_date",today());v.put("notes",notes);v.put("next_service",nextService);v.put("created_at",now());long saved=getWritableDatabase().insert("maintenance_logs",null,v);queueSync("maintenance_log",saved,"upsert");if(nextService!=null&&!nextService.isEmpty()){ContentValues a=new ContentValues();a.put("next_service",nextService);getWritableDatabase().update("assets",a,"id=?",new String[]{String.valueOf(assetId)});}queueSync("asset",assetId,"upsert");if(jobId>0)queueSync("job",jobId,"upsert");}
    public void completeMaintenanceIfNeeded(long assetId,long jobId,String notes,String nextService){if(jobId>0&&count("maintenance_logs","job_id=?",new String[]{String.valueOf(jobId)})>0)return;completeMaintenance(assetId,jobId,notes,nextService);}

    public void clearOperationalData(){
        SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{d.delete("job_assignment_history",null,null);d.delete("maintenance_logs",null,null);d.delete("job_photos",null,null);d.delete("jobs",null,null);d.delete("assets",null,null);d.delete("customer_sites",null,null);d.delete("sites",null,null);d.delete("customers",null,null);d.delete("sequences",null,null);d.delete("sync_queue","entity_type IN ('customer','site','customer_site','asset','job','job_photo','maintenance_log','job_signature')",null);d.delete("sync_conflicts","entity_type IN ('customer','site','asset','job','job_photo','maintenance_log')",null);d.delete("sync_metadata","entity_type IN ('customer','site','asset','job','job_photo','maintenance_log','job_signature')",null);d.setTransactionSuccessful();}finally{d.endTransaction();}
    }

    public JSONObject exportJson() throws Exception {
        JSONObject root=new JSONObject();root.put("format","FidaFieldBackup");root.put("version",1);root.put("exported_at",now());
        String[] tables={"customers","sites","customer_sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};
        SQLiteDatabase db=getReadableDatabase();
        for(String table:tables){JSONArray arr=new JSONArray();Cursor c=db.rawQuery("SELECT * FROM "+table,null);try{while(c.moveToNext()){JSONObject o=new JSONObject();for(int i=0;i<c.getColumnCount();i++){if(c.isNull(i))o.put(c.getColumnName(i),JSONObject.NULL);else o.put(c.getColumnName(i),c.getString(i));}arr.put(o);}}finally{c.close();}root.put(table,arr);}return root;
    }

    public void importJson(JSONObject root) throws Exception {
        String[] tables={"job_assignment_history","maintenance_logs","job_photos","jobs","assets","customer_sites","sites","customers","technicians","sequences"}; SQLiteDatabase db=getWritableDatabase(); db.beginTransaction();
        try{for(String t:tables)db.delete(t,null,null);db.delete("sync_queue",null,null);String[] order={"customers","sites","customer_sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};for(String t:order){JSONArray arr=root.optJSONArray(t);if(arr==null)continue;for(int i=0;i<arr.length();i++){JSONObject o=arr.getJSONObject(i);ContentValues v=new ContentValues();java.util.Iterator<String> it=o.keys();while(it.hasNext()){String k=it.next();if(o.isNull(k))v.putNull(k);else v.put(k,o.getString(k));}db.insertOrThrow(t,null,v);}}String stamp=now();queueExistingForSync(db,"customer","customers",stamp);queueExistingForSync(db,"site","sites",stamp);db.execSQL("INSERT OR IGNORE INTO customer_sites(customer_id,site_id) SELECT customer_id,id FROM sites WHERE customer_id IS NOT NULL");db.execSQL("INSERT OR REPLACE INTO sync_queue(entity_type,entity_id,operation,changed_at) SELECT 'customer_site',id,'upsert',? FROM sites",new Object[]{stamp});queueExistingForSync(db,"asset","assets",stamp);queueExistingForSync(db,"job","jobs",stamp);queueExistingForSync(db,"technician","technicians",stamp);queueExistingForSync(db,"job_photo","job_photos",stamp);queueExistingForSync(db,"maintenance_log","maintenance_logs",stamp);db.execSQL("INSERT OR REPLACE INTO sync_queue(entity_type,entity_id,operation,changed_at) SELECT 'job_signature',id,'upsert',? FROM jobs WHERE signature_path IS NOT NULL AND signature_path<>''",new Object[]{stamp});db.setTransactionSuccessful();}finally{db.endTransaction();}
    }

    public void insertDemoData() {
        if(count("customers",null,null)>0)return;
        long c1=saveCustomer(0,map("name","Kigali Business Center","contact","Alice","phone","+250 788 000 001","email","alice@example.com","address","Kigali","notes","Demo customer"));
        long s1=saveSite(0,map("customer_id",String.valueOf(c1),"name","Main Office","address","Kigali","contact","Eric","phone","+250 788 000 002","notes",""));setSiteCustomers(s1,java.util.Collections.singletonList(c1));
        saveAsset(0,map("customer_id",String.valueOf(c1),"site_id",String.valueOf(s1),"tag","AST-00001","name","Main UPS","category","UPS / Power","make_model","APC Smart-UPS","serial","DEMO-001","location","Server Room","notes","Quarterly inspection","interval_days","90","next_service",today()));
    }

    public static Map<String,String> map(String... kv){HashMap<String,String> m=new HashMap<>();for(int i=0;i+1<kv.length;i+=2)m.put(kv[i],kv[i+1]);return m;}
}
