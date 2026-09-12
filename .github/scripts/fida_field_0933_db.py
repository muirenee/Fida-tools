from pathlib import Path

p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
s=p.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'0.9.33 DB patch failed: {label}')
    s=s.replace(old,new,1)

rep('    public static final int DB_VERSION = 9;','    public static final int DB_VERSION = 10;','db version')

anchor='        db.execSQL("CREATE TABLE assets (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, site_id INTEGER, tag TEXT NOT NULL UNIQUE, name TEXT NOT NULL, category TEXT, make_model TEXT, serial TEXT, location TEXT, notes TEXT, interval_days INTEGER DEFAULT 0, next_service TEXT, created_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE SET NULL)");\n'
insert='        db.execSQL("CREATE TABLE customer_sites (customer_id INTEGER NOT NULL, site_id INTEGER NOT NULL, PRIMARY KEY(customer_id,site_id), FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE)");\n        db.execSQL("CREATE INDEX idx_customer_sites_customer ON customer_sites(customer_id,site_id)");\n        db.execSQL("CREATE INDEX idx_customer_sites_site ON customer_sites(site_id,customer_id)");\n'+anchor
rep(anchor,insert,'customer_sites onCreate')

anchor='        if(oldVersion<9){\n            db.execSQL("ALTER TABLE jobs ADD COLUMN technician_id INTEGER");\n            db.execSQL("UPDATE jobs SET technician_id=(SELECT t.id FROM technicians t WHERE lower(trim(t.name))=lower(trim(jobs.technician)) ORDER BY t.id LIMIT 1) WHERE technician_id IS NULL AND technician IS NOT NULL AND trim(technician)<>\'\'");\n            db.execSQL("CREATE TABLE IF NOT EXISTS job_assignment_history (id INTEGER PRIMARY KEY AUTOINCREMENT, remote_uuid TEXT UNIQUE, job_id INTEGER NOT NULL, from_technician_id INTEGER, to_technician_id INTEGER, from_technician_name TEXT, to_technician_name TEXT, changed_by TEXT, changed_at TEXT NOT NULL, pending INTEGER DEFAULT 0, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_job_assignment_history_job ON job_assignment_history(job_id,changed_at)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_jobs_technician_id ON jobs(technician_id)");\n        }\n'
new=anchor+'        if(oldVersion<10){\n            db.execSQL("CREATE TABLE IF NOT EXISTS customer_sites (customer_id INTEGER NOT NULL, site_id INTEGER NOT NULL, PRIMARY KEY(customer_id,site_id), FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_customer ON customer_sites(customer_id,site_id)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_site ON customer_sites(site_id,customer_id)");\n            db.execSQL("INSERT OR IGNORE INTO customer_sites(customer_id,site_id) SELECT customer_id,id FROM sites WHERE customer_id IS NOT NULL");\n        }\n'
rep(anchor,new,'customer_sites upgrade')

old='''    public List<Row> sites(long customerId) {
        return rows("SELECT s.*, c.name customer_name FROM sites s LEFT JOIN customers c ON c.id=s.customer_id " + (customerId > 0 ? "WHERE s.customer_id=? " : "") + "ORDER BY c.name,s.name", customerId > 0 ? new String[]{String.valueOf(customerId)} : null);
    }
'''
new='''    public List<Row> sites(long customerId) {
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
'''
rep(old,new,'site queries and mappings')

rep("    public long pendingBusinessChanges(){return count(\"sync_queue\",\"entity_type IN ('customer','site','asset','technician','job','job_photo','maintenance_log','job_signature')\",null);}","    public long pendingBusinessChanges(){return count(\"sync_queue\",\"entity_type IN ('customer','site','customer_site','asset','technician','job','job_photo','maintenance_log','job_signature')\",null);}",'pending customer_site')
rep("    public void discardManagerOnlyPendingChanges(){getWritableDatabase().delete(\"sync_queue\",\"entity_type IN ('customer','site','asset','technician')\",null);getWritableDatabase().delete(\"sync_conflicts\",\"entity_type IN ('customer','site','asset','technician')\",null);}","    public void discardManagerOnlyPendingChanges(){getWritableDatabase().delete(\"sync_queue\",\"entity_type IN ('customer','site','customer_site','asset','technician')\",null);getWritableDatabase().delete(\"sync_conflicts\",\"entity_type IN ('customer','site','asset','technician')\",null);}",'discard customer_site')

old='''    public void deleteById(String table,long id){
        if(id<=0)return;
        if("customers".equals(table)){for(Row r:rows("SELECT id FROM sites WHERE customer_id=?",new String[]{String.valueOf(id)}))queueSync("site",r.id(),"delete");}
        else if("assets".equals(table)){for(Row r:rows("SELECT id FROM maintenance_logs WHERE asset_id=?",new String[]{String.valueOf(id)}))queueSync("maintenance_log",r.id(),"delete");}
        else if("jobs".equals(table)){for(Row r:photos(id))queueSync("job_photo",r.id(),"delete");queueSync("job_signature",id,"delete");}
        String type=table.endsWith("s")?table.substring(0,table.length()-1):table;queueSync(type,id,"delete");getWritableDatabase().delete(table,"id=?",new String[]{String.valueOf(id)});
    }
'''
new='''    private void rehomeSharedSitesBeforeCustomerDelete(long customerId,boolean queueChanges){
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
'''
rep(old,new,'shared site deletion')

old='''    public boolean applyRemoteDeletion(String type,String remoteUuid){long local=localIdForRemote(type,remoteUuid);if(local<=0)return false;if(hasPendingSync(type,local)||hasPendingDependents(type,local)){recordSyncConflict(type,local,remoteUuid,"Cloud deletion deferred because this device has unsynced work");return false;}String table=localTableForType(type);if(table.isEmpty())return false;SQLiteDatabase d=getWritableDatabase();d.delete(table,"id=?",new String[]{String.valueOf(local)});markDeletionSynced(type,local,remoteUuid);return true;}
'''
new='''    public boolean applyRemoteDeletion(String type,String remoteUuid){long local=localIdForRemote(type,remoteUuid);if(local<=0)return false;if(hasPendingSync(type,local)||hasPendingDependents(type,local)){recordSyncConflict(type,local,remoteUuid,"Cloud deletion deferred because this device has unsynced work");return false;}String table=localTableForType(type);if(table.isEmpty())return false;SQLiteDatabase d=getWritableDatabase();if("customer".equals(type))rehomeSharedSitesBeforeCustomerDelete(local,false);d.delete(table,"id=?",new String[]{String.valueOf(local)});markDeletionSynced(type,local,remoteUuid);return true;}
'''
rep(old,new,'remote shared customer delete')

anchor='''    public JSONObject exportJson() throws Exception {
'''
clear='''    public void clearOperationalData(){
        SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{d.delete("job_assignment_history",null,null);d.delete("maintenance_logs",null,null);d.delete("job_photos",null,null);d.delete("jobs",null,null);d.delete("assets",null,null);d.delete("customer_sites",null,null);d.delete("sites",null,null);d.delete("customers",null,null);d.delete("sequences",null,null);d.delete("sync_queue","entity_type IN ('customer','site','customer_site','asset','job','job_photo','maintenance_log','job_signature')",null);d.delete("sync_conflicts","entity_type IN ('customer','site','asset','job','job_photo','maintenance_log')",null);d.delete("sync_metadata","entity_type IN ('customer','site','asset','job','job_photo','maintenance_log','job_signature')",null);d.setTransactionSuccessful();}finally{d.endTransaction();}
    }

'''+anchor
rep(anchor,clear,'clear operational data')

rep('String[] tables={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};','String[] tables={"customers","sites","customer_sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};','backup customer_sites')
rep('String[] tables={"job_assignment_history","maintenance_logs","job_photos","jobs","assets","sites","customers","technicians","sequences"}; SQLiteDatabase db=getWritableDatabase(); db.beginTransaction();','String[] tables={"job_assignment_history","maintenance_logs","job_photos","jobs","assets","customer_sites","sites","customers","technicians","sequences"}; SQLiteDatabase db=getWritableDatabase(); db.beginTransaction();','restore delete customer_sites')
rep('String[] order={"customers","sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};','String[] order={"customers","sites","customer_sites","assets","jobs","job_photos","maintenance_logs","technicians","job_assignment_history","sequences"};','restore order customer_sites')
rep('queueExistingForSync(db,"site","sites",stamp);queueExistingForSync(db,"asset","assets",stamp);','queueExistingForSync(db,"site","sites",stamp);db.execSQL("INSERT OR IGNORE INTO customer_sites(customer_id,site_id) SELECT customer_id,id FROM sites WHERE customer_id IS NOT NULL");db.execSQL("INSERT OR REPLACE INTO sync_queue(entity_type,entity_id,operation,changed_at) SELECT \'customer_site\',id,\'upsert\',? FROM sites",new Object[]{stamp});queueExistingForSync(db,"asset","assets",stamp);','restore queue site links')
rep('long s1=saveSite(0,map("customer_id",String.valueOf(c1),"name","Main Office","address","Kigali","contact","Eric","phone","+250 788 000 002","notes",""));\n        saveAsset','long s1=saveSite(0,map("customer_id",String.valueOf(c1),"name","Main Office","address","Kigali","contact","Eric","phone","+250 788 000 002","notes",""));setSiteCustomers(s1,java.util.Collections.singletonList(c1));\n        saveAsset','demo site link')

p.write_text(s)
print('Fida Field 0.9.33 AppDatabase patch applied')
