from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

# 0.9.18: reconcile a local technician with an already-existing cloud technician
# when both represent the same authenticated workspace user.
p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
s = p.read_text()
if 'reconcileTechnicianIdentity(' not in s:
    anchor = '''    public List<Row> jobsForAsset(long assetId){return rows("SELECT j.*,c.name customer_name FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id WHERE j.asset_id=? ORDER BY j.job_date DESC,j.id DESC",new String[]{String.valueOf(assetId)});}\n'''
    helper = '''    public long reconcileTechnicianIdentity(long sourceId,long targetId,String remoteUuid){\n        if(sourceId<=0)return targetId;if(targetId<=0||sourceId==targetId){bindRemoteUuid("technician",sourceId,remoteUuid);return sourceId;}\n        Row src=getTechnician(sourceId),target=getTechnician(targetId);if(src.id()==0){bindRemoteUuid("technician",targetId,remoteUuid);return targetId;}if(target.id()==0){bindRemoteUuid("technician",sourceId,remoteUuid);return sourceId;}\n        SQLiteDatabase d=getWritableDatabase();d.beginTransaction();try{\n            ContentValues v=new ContentValues();v.put("name",src.s("name"));v.put("role",src.s("role"));v.put("phone",src.s("phone"));v.put("email",src.s("email"));String user=src.s("user_uuid");if(user.isEmpty())v.putNull("user_uuid");else v.put("user_uuid",user);v.put("active",src.i("active"));d.update("technicians",v,"id=?",new String[]{String.valueOf(targetId)});\n            ContentValues jv=new ContentValues();jv.put("technician_id",targetId);jv.put("technician",src.s("name"));d.update("jobs",jv,"technician_id=?",new String[]{String.valueOf(sourceId)});\n            ContentValues fv=new ContentValues();fv.put("from_technician_id",targetId);d.update("job_assignment_history",fv,"from_technician_id=?",new String[]{String.valueOf(sourceId)});ContentValues tv=new ContentValues();tv.put("to_technician_id",targetId);d.update("job_assignment_history",tv,"to_technician_id=?",new String[]{String.valueOf(sourceId)});\n            d.delete("sync_queue","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(sourceId)});d.delete("sync_conflicts","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(sourceId)});d.delete("sync_metadata","entity_type='technician' AND entity_id=?",new String[]{String.valueOf(sourceId)});d.delete("technicians","id=?",new String[]{String.valueOf(sourceId)});\n            Row meta=one("SELECT id FROM sync_metadata WHERE entity_type='technician' AND entity_id=?",new String[]{String.valueOf(targetId)});ContentValues mv=new ContentValues();mv.put("remote_uuid",remoteUuid);if(meta.id()>0)d.update("sync_metadata",mv,"id=?",new String[]{String.valueOf(meta.id())});else{mv.put("entity_type","technician");mv.put("entity_id",targetId);d.insertOrThrow("sync_metadata",null,mv);}\n            ContentValues qv=new ContentValues();qv.put("entity_type","technician");qv.put("entity_id",targetId);qv.put("operation","upsert");qv.put("changed_at",now());d.insertWithOnConflict("sync_queue",null,qv,SQLiteDatabase.CONFLICT_REPLACE);\n            d.setTransactionSuccessful();\n        }finally{d.endTransaction();}\n        return targetId;\n    }\n\n'''
    s = replace_once(s, anchor, helper + anchor, 'technician identity reconciliation helper')
    p.write_text(s)

p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s = p.read_text()
if 'canonicalTechnicianRemoteId(' not in s:
    anchor = '''    private void syncAssignmentHistory(String workspaceId)throws Exception{JSONArray history=client.select("job_assignment_history","select=*&workspace_id=eq."+workspaceId+"&order=changed_at.asc");db.cacheAssignmentHistory(history);}\n'''
    helper = '''    private String canonicalTechnicianRemoteId(String workspaceId,JSONObject body)throws Exception{\n        if(body==null||body.isNull("user_id"))return "";String user=body.optString("user_id","").trim();if(user.isEmpty())return "";JSONArray rows=client.select("technicians","select=id&workspace_id=eq."+workspaceId+"&user_id=eq."+user+"&deleted_at=is.null&limit=1");return rows.length()>0?rows.getJSONObject(0).optString("id",""):"";\n    }\n\n'''
    s = replace_once(s, anchor, helper + anchor, 'cloud technician identity lookup')

if 'reconcileTechnicianIdentity(localId,mappedLocal,canonical)' not in s:
    old = '''String remoteId=body.optString("id");if("job".equals(type)&&!canManage'''
    new = '''String remoteId=body.optString("id");if("technician".equals(type)){String canonical=canonicalTechnicianRemoteId(workspaceId,body);if(!canonical.isEmpty()&&!canonical.equals(remoteId)){long mappedLocal=db.localIdForRemote("technician",canonical);if(mappedLocal>0&&mappedLocal!=localId)localId=db.reconcileTechnicianIdentity(localId,mappedLocal,canonical);else db.bindRemoteUuid("technician",localId,canonical);body.put("id",canonical);remoteId=canonical;}}if("job".equals(type)&&!canManage'''
    s = replace_once(s, old, new, 'technician push reconciliation')
p.write_text(s)

# Bump the test build so it installs as an update over 0.9.17.
p = Path('fida-field/app/build.gradle')
s = p.read_text()
if "versionName '0.9.18-test'" not in s:
    s = replace_once(s, '        versionCode 20\n        versionName \'0.9.17-test\'', '        versionCode 21\n        versionName \'0.9.18-test\'', '0.9.18 version bump')
p.write_text(s)

print('Fida Field 0.9.18 technician identity reconciliation applied')
