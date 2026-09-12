from pathlib import Path

p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s=p.read_text()

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'0.9.33 cloud patch failed: {label}')
    s=s.replace(old,new,1)

anchor='    private String serviceTypesCacheKey(String workspaceId){return "service_types_json_"+(workspaceId==null||workspaceId.trim().isEmpty()?"local":workspaceId.trim());}\n'
methods='''    private String operationalGenerationKey(String workspaceId){return "workspace_operational_generation_"+(workspaceId==null?"":workspaceId.trim());}
    private long rpcLong(Object raw){if(raw==null)return 0;if(raw instanceof Number)return ((Number)raw).longValue();if(raw instanceof JSONArray&&((JSONArray)raw).length()>0)return ((JSONArray)raw).optLong(0,0);try{return Long.parseLong(String.valueOf(raw).replace("\\\"","").trim());}catch(Exception e){return 0;}}
    private long workspaceOperationalGeneration(String workspaceId)throws Exception{Object raw=client.rpc("get_workspace_operational_generation",new JSONObject().put("p_workspace_id",workspaceId));long value=rpcLong(raw);return value<=0?1:value;}
    private void clearLocalOperationalMedia(){
        try{JSONObject snap=db.exportJson();JSONArray photos=snap.optJSONArray("job_photos");if(photos!=null)for(int i=0;i<photos.length();i++){JSONObject o=photos.optJSONObject(i);String u=o==null?"":o.optString("uri","");try{if(u.startsWith("content://"))context.getContentResolver().delete(android.net.Uri.parse(u),null,null);else if(u.startsWith("file://")){String path=android.net.Uri.parse(u).getPath();if(path!=null)new java.io.File(path).delete();}}catch(Exception ignored){}}JSONArray jobs=snap.optJSONArray("jobs");if(jobs!=null)for(int i=0;i<jobs.length();i++){JSONObject o=jobs.optJSONObject(i);String path=o==null?"":o.optString("signature_path","");if(!path.isEmpty())try{new java.io.File(path).delete();}catch(Exception ignored){}}}catch(Exception ignored){}
    }
    private void alignOperationalGeneration(String workspaceId)throws Exception{
        long cloud=workspaceOperationalGeneration(workspaceId),local=prefs.getLong(operationalGenerationKey(workspaceId),0L);if(local==0L){if(cloud>1L){clearLocalOperationalMedia();db.clearOperationalData();}prefs.edit().putLong(operationalGenerationKey(workspaceId),cloud).apply();return;}if(cloud>local){clearLocalOperationalMedia();db.clearOperationalData();prefs.edit().putLong(operationalGenerationKey(workspaceId),cloud).apply();}else if(cloud<local)prefs.edit().putLong(operationalGenerationKey(workspaceId),cloud).apply();
    }

    public long resetWorkspaceOperationalData(String workspaceId)throws Exception{
        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.trim().isEmpty())throw new Exception("Cloud workspace is not bound");String wid=workspaceId.trim();
        JSONArray photos=client.select("job_photos","select=storage_path&workspace_id=eq."+wid);JSONArray jobs=client.select("jobs","select=signature_path&workspace_id=eq."+wid);Object raw=client.rpc("reset_workspace_operational_data",new JSONObject().put("p_workspace_id",wid));long generation=rpcLong(raw);if(generation<=0)throw new Exception("Workspace reset did not return a generation");
        for(int i=0;i<photos.length();i++){String path=photos.optJSONObject(i)==null?"":photos.optJSONObject(i).optString("storage_path","");if(!path.isEmpty())try{client.deleteObject(CloudMediaSync.BUCKET,path);}catch(Exception ignored){}}
        for(int i=0;i<jobs.length();i++){String path=jobs.optJSONObject(i)==null?"":jobs.optJSONObject(i).optString("signature_path","");if(!path.isEmpty())try{client.deleteObject(CloudMediaSync.BUCKET,path);}catch(Exception ignored){}}
        clearLocalOperationalMedia();db.clearOperationalData();prefs.edit().putLong(operationalGenerationKey(wid),generation).apply();return generation;
    }

    public void syncCustomerSites(String workspaceId,boolean canManage)throws Exception{
        if(workspaceId==null||workspaceId.trim().isEmpty()||!backendConfigured()||!signedIn())return;String wid=workspaceId.trim();
        if(canManage&&db.hasCustomerSiteLinkChanges()){
            JSONArray cloud=client.select("customer_sites","select=id,customer_id,site_id,active&workspace_id=eq."+wid);java.util.HashSet<String> keep=new java.util.HashSet<>();
            for(AppDatabase.Row link:db.customerSiteLinks()){long cid=parseLong(link.s("customer_id")),sid=parseLong(link.s("site_id"));if(cid<=0||sid<=0)continue;String cr=db.ensureRemoteUuid("customer",cid),sr=db.ensureRemoteUuid("site",sid),key=cr+"|"+sr;keep.add(key);JSONObject body=new JSONObject().put("workspace_id",wid).put("customer_id",cr).put("site_id",sr).put("active",true).put("updated_by",userId()).put("updated_at",isoNow());client.upsert("customer_sites","workspace_id,customer_id,site_id",body);}
            for(int i=0;i<cloud.length();i++){JSONObject o=cloud.optJSONObject(i);if(o==null||!o.optBoolean("active",true))continue;String key=o.optString("customer_id","")+"|"+o.optString("site_id","");if(!keep.contains(key)){String id=o.optString("id","");if(!id.isEmpty())client.update("customer_sites","id=eq."+id,new JSONObject().put("active",false).put("updated_by",userId()).put("updated_at",isoNow()));}}
            db.markCustomerSiteLinksSynced();
        }
        JSONArray rows=client.select("customer_sites","select=customer_id,site_id&workspace_id=eq."+wid+"&active=eq.true&order=created_at.asc");db.replaceCustomerSiteLinksFromCloud(rows);
    }

'''+anchor
rep(anchor,methods,'cloud reset + customer site methods')

old='            WorkspaceMembership verified=refreshWorkspaceAccess(workspaceId);if(verified==null)throw new Exception("Workspace access is disabled or has been removed. Ask the workspace Owner/Admin to re-enable your account, then check access again.");canManage=AccountTeamManager.ROLE_OWNER.equals(verified.role)||AccountTeamManager.ROLE_ADMIN.equals(verified.role);\n            int pushed=0,pulled=0,deferred=0;'
new='            WorkspaceMembership verified=refreshWorkspaceAccess(workspaceId);if(verified==null)throw new Exception("Workspace access is disabled or has been removed. Ask the workspace Owner/Admin to re-enable your account, then check access again.");canManage=AccountTeamManager.ROLE_OWNER.equals(verified.role)||AccountTeamManager.ROLE_ADMIN.equals(verified.role);alignOperationalGeneration(workspaceId);\n            int pushed=0,pulled=0,deferred=0;'
rep(old,new,'generation gate in sync')

old='            if(!canManage)db.pruneInvisibleCloudJobs(visibleJobIds);\n            syncBranding(workspaceId,canManage);\n            syncServiceTypes(workspaceId,canManage);\n'
new='            if(!canManage)db.pruneInvisibleCloudJobs(visibleJobIds);\n            syncCustomerSites(workspaceId,canManage);\n            syncBranding(workspaceId,canManage);\n            syncServiceTypes(workspaceId,canManage);\n'
rep(old,new,'customer sites in sync')

p.write_text(s)
print('Fida Field 0.9.33 CloudSyncFoundation patch applied')
