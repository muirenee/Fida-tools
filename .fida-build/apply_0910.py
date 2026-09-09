from pathlib import Path

root = Path('fida-field')
db_path = root / 'app/src/main/java/com/fidalix/fidafield/AppDatabase.java'
main_path = root / 'app/src/main/java/com/fidalix/fidafield/MainActivity.java'
gradle_path = root / 'app/build.gradle'
readme_path = root / 'README.md'

s = db_path.read_text()
assert 'DB_VERSION = 5' in s, 'expected DB version 5'
s = s.replace('DB_VERSION = 5', 'DB_VERSION = 6', 1)

upgrade_marker = '''        if(oldVersion<5){
            db.execSQL("ALTER TABLE workspace_members ADD COLUMN user_uuid TEXT");
            db.execSQL("ALTER TABLE workspace_invites ADD COLUMN token TEXT");
            db.execSQL("ALTER TABLE workspace_invites ADD COLUMN expires_at TEXT");
        }
'''
assert upgrade_marker in s, '0.9.9 DB upgrade marker not found'
s = s.replace(upgrade_marker, upgrade_marker + '''        if(oldVersion<6){
            String stamp=now();
            queueExistingForSync(db,"job_photo","job_photos",stamp);
            queueExistingForSync(db,"maintenance_log","maintenance_logs",stamp);
            db.execSQL("INSERT OR REPLACE INTO sync_queue(entity_type,entity_id,operation,changed_at) SELECT 'job_signature',id,'upsert',? FROM jobs WHERE signature_path IS NOT NULL AND signature_path<>''",new Object[]{stamp});
        }
''', 1)

old_pending = '''    public long pendingBusinessChanges(){return count("sync_queue","entity_type IN ('customer','site','asset','technician','job')",null);}'''
new_pending = '''    public long pendingBusinessChanges(){return count("sync_queue","entity_type IN ('customer','site','asset','technician','job','job_photo','maintenance_log','job_signature')",null);}'''
assert old_pending in s, 'pending change counter not found'
s = s.replace(old_pending, new_pending, 1)

old_photo = '''    public void addPhoto(long jobId,String uri){ContentValues v=new ContentValues();v.put("job_id",jobId);v.put("uri",uri);v.put("caption","");v.put("created_at",now());getWritableDatabase().insert("job_photos",null,v);queueSync("job",jobId,"upsert");}'''
new_photo = '''    public void addPhoto(long jobId,String uri){ContentValues v=new ContentValues();v.put("job_id",jobId);v.put("uri",uri);v.put("caption","");v.put("created_at",now());long saved=getWritableDatabase().insert("job_photos",null,v);queueSync("job_photo",saved,"upsert");queueSync("job",jobId,"upsert");}'''
assert old_photo in s, 'photo save method not found'
s = s.replace(old_photo, new_photo, 1)

old_sig = '''    public void setSignature(long jobId,String path,String signer){ContentValues v=new ContentValues();v.put("signature_path",path);v.put("customer_name_signed",signer);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");}'''
new_sig = '''    public void setSignature(long jobId,String path,String signer){ContentValues v=new ContentValues();v.put("signature_path",path);v.put("customer_name_signed",signer);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");queueSync("job_signature",jobId,"upsert");}'''
assert old_sig in s, 'signature save method not found'
s = s.replace(old_sig, new_sig, 1)

old_maint = '''    public void completeMaintenance(long assetId,long jobId,String notes,String nextService){ContentValues v=new ContentValues();v.put("asset_id",assetId);if(jobId>0)v.put("job_id",jobId);v.put("service_date",today());v.put("notes",notes);v.put("next_service",nextService);v.put("created_at",now());getWritableDatabase().insert("maintenance_logs",null,v);if(nextService!=null&&!nextService.isEmpty()){ContentValues a=new ContentValues();a.put("next_service",nextService);getWritableDatabase().update("assets",a,"id=?",new String[]{String.valueOf(assetId)});}queueSync("asset",assetId,"upsert");if(jobId>0)queueSync("job",jobId,"upsert");}'''
new_maint = '''    public void completeMaintenance(long assetId,long jobId,String notes,String nextService){ContentValues v=new ContentValues();v.put("asset_id",assetId);if(jobId>0)v.put("job_id",jobId);v.put("service_date",today());v.put("notes",notes);v.put("next_service",nextService);v.put("created_at",now());long saved=getWritableDatabase().insert("maintenance_logs",null,v);queueSync("maintenance_log",saved,"upsert");if(nextService!=null&&!nextService.isEmpty()){ContentValues a=new ContentValues();a.put("next_service",nextService);getWritableDatabase().update("assets",a,"id=?",new String[]{String.valueOf(assetId)});}queueSync("asset",assetId,"upsert");if(jobId>0)queueSync("job",jobId,"upsert");}'''
assert old_maint in s, 'maintenance save method not found'
s = s.replace(old_maint, new_maint, 1)

# A restored backup must also upload its media/history on the next cloud sync.
idx = s.index('    public void importJson(JSONObject root)')
prefix, tail = s[:idx], s[idx:]
old_import_end = '''queueExistingForSync(db,"technician","technicians",stamp);db.setTransactionSuccessful();'''
new_import_end = '''queueExistingForSync(db,"technician","technicians",stamp);queueExistingForSync(db,"job_photo","job_photos",stamp);queueExistingForSync(db,"maintenance_log","maintenance_logs",stamp);db.execSQL("INSERT OR REPLACE INTO sync_queue(entity_type,entity_id,operation,changed_at) SELECT 'job_signature',id,'upsert',? FROM jobs WHERE signature_path IS NOT NULL AND signature_path<>''",new Object[]{stamp});db.setTransactionSuccessful();'''
assert old_import_end in tail, 'backup sync queue marker not found'
tail = tail.replace(old_import_end, new_import_end, 1)
s = prefix + tail

db_path.write_text(s)

m = main_path.read_text()
old_ctor = 'cloudSync=new CloudSyncFoundation(prefs,db);'
assert old_ctor in m, 'CloudSyncFoundation constructor marker not found'
m = m.replace(old_ctor, 'cloudSync=new CloudSyncFoundation(this,prefs,db);', 1)
m = m.replace('Fida Field 0.9.9 Test', 'Fida Field 0.9.10 Test')
main_path.write_text(m)

g = gradle_path.read_text()
assert 'versionCode 12' in g and "versionName '0.9.9-test'" in g, '0.9.9 version markers not found'
g = g.replace('versionCode 12', 'versionCode 13', 1)
g = g.replace("versionName '0.9.9-test'", "versionName '0.9.10-test'", 1)
gradle_path.write_text(g)

if readme_path.exists():
    r = readme_path.read_text().replace('0.9.9-test','0.9.10-test').replace('versionCode 12','versionCode 13')
    readme_path.write_text(r)
