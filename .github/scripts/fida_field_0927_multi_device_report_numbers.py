from pathlib import Path

appdb_path = Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
cloud_path = Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
gradle_path = Path('fida-field/app/build.gradle')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'0.9.27 patch failed: {label} pattern not found')
    return text.replace(old, new, 1)

# Local database helpers used to keep first-sync cloud numbering collision-free.
s = appdb_path.read_text()
old = '    public boolean hasPendingSync(String type,long localId){return localId>0&&count("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)})>0;}\n'
new = '''    public boolean hasEverSynced(String type,long localId){return localId>0&&count("sync_metadata","entity_type=? AND entity_id=? AND last_synced_at IS NOT NULL AND trim(last_synced_at)<>''",new String[]{type,String.valueOf(localId)})>0;}\n    public long maxLocalReportSequence(String reportNo){\n        if(reportNo==null)return 0;String value=reportNo.trim().toUpperCase(Locale.US);int last=value.lastIndexOf('-');if(last<1||last>=value.length()-1)return 0;String stem=value.substring(0,last+1);long max=0;\n        for(Row r:rows("SELECT report_no FROM jobs WHERE upper(report_no) LIKE ?",new String[]{stem+"%"})){String n=r.s("report_no").trim().toUpperCase(Locale.US);if(!n.startsWith(stem))continue;try{max=Math.max(max,Long.parseLong(n.substring(stem.length())));}catch(Exception ignored){}}return max;\n    }\n    public void updateJobReportNoFromCloud(long jobId,String reportNo){if(jobId<=0||reportNo==null||reportNo.trim().isEmpty())return;ContentValues v=new ContentValues();v.put("report_no",reportNo.trim().toUpperCase(Locale.US));v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});}\n    public boolean hasPendingSync(String type,long localId){return localId>0&&count("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(localId)})>0;}\n'''
s = replace_once(s, old, new, 'AppDatabase first-sync helpers')
appdb_path.write_text(s)

# Reserve/claim a workspace-unique report number before the first cloud upsert.
s = cloud_path.read_text()
s = replace_once(
    s,
    'if(localId<=0)continue;JSONObject body=payload(type,localId,workspaceId);',
    'if(localId<=0)continue;if("job".equals(type)&&!db.hasEverSynced("job",localId))reserveReportNumberForFirstSync(localId,workspaceId);JSONObject body=payload(type,localId,workspaceId);',
    'job first-sync reservation hook'
)

anchor = '    private String canonicalTechnicianRemoteId(String workspaceId,JSONObject body)throws Exception{\n'
method = '''    private void reserveReportNumberForFirstSync(long localId,String workspaceId)throws Exception{\n        if(localId<=0||db.hasEverSynced("job",localId))return;AppDatabase.Row job=db.syncEntity("job",localId);if(job.id()==0)return;String requested=job.s("report_no");String remoteId=db.ensureRemoteUuid("job",localId);long localMax=db.maxLocalReportSequence(requested);\n        Object raw=client.rpc("reserve_report_number",new JSONObject().put("p_workspace_id",workspaceId).put("p_job_id",remoteId).put("p_requested_report_no",requested).put("p_local_max_seq",localMax));String reserved=rpcString(raw);\n        if(reserved.isEmpty())throw new Exception("Could not reserve a workspace report number");if(!reserved.equalsIgnoreCase(requested))db.updateJobReportNoFromCloud(localId,reserved);\n    }\n\n'''
s = replace_once(s, anchor, method + anchor, 'reserve report number method')
cloud_path.write_text(s)

# Version bump.
g = gradle_path.read_text()
g = replace_once(g, '        versionCode 29\n', '        versionCode 30\n', 'version code')
g = replace_once(g, "        versionName '0.9.26-test'\n", "        versionName '0.9.27-test'\n", 'version name')
gradle_path.write_text(g)

print('Fida Field 0.9.27 multi-device report numbering applied')
