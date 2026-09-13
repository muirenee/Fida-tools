package com.fidalix.fidafield;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.List;
import java.util.UUID;

/** Offline-first Supabase synchronization layer. Local edits remain queued until the
 * server acknowledges them. Core business entities are pushed in dependency order and
 * then current workspace records and private Storage media are synchronized. */
public class CloudSyncFoundation {
    public static final String PROVIDER="Supabase";
    private static final Object SYNC_LOCK=new Object();
    public static final String KEY_WORKSPACE_ACCESS_STATE="cloud_workspace_access_state";
    public static final String KEY_WORKSPACE_ACCESS_ID="cloud_workspace_access_id";
    public static final String KEY_WORKSPACE_ACCESS_CHECKED_AT="cloud_workspace_access_checked_at";
    public static final String ACCESS_ACTIVE="Active";
    public static final String ACCESS_REVOKED="Revoked";
    public static final String ACCESS_UNKNOWN="Unknown";
    private final Context context;
    private final SharedPreferences prefs;
    private final AppDatabase db;
    private final SupabaseClientLite client;

    public static class WorkspaceMembership {
        public final String id,name,role;
        public WorkspaceMembership(String id,String name,String role){this.id=id;this.name=name;this.role=role;}
    }
    public static class SyncResult {
        public final int pushed,pulled;
        public final String message;
        public SyncResult(int pushed,int pulled,String message){this.pushed=pushed;this.pulled=pulled;this.message=message;}
    }

    public CloudSyncFoundation(Context context,SharedPreferences prefs,AppDatabase db){this.context=context.getApplicationContext();this.prefs=prefs;this.db=db;this.client=new SupabaseClientLite(prefs);}

    public String deviceId(){String id=prefs.getString("cloud_device_id","");if(id==null||id.isEmpty()){id=UUID.randomUUID().toString();prefs.edit().putString("cloud_device_id",id).apply();}return id;}
    public long pendingChanges(){return db.pendingBusinessChanges();}
    public long conflictCount(){return db.unresolvedConflictCount();}
    public String providerName(){return PROVIDER;}
    public boolean backendConfigured(){return client.configured();}
    public boolean signedIn(){return client.hasStoredSession();}
    public String accountEmail(){return client.accountEmail();}
    public String userId(){return client.userId();}
    public String lastSync(){String v=prefs.getString("cloud_last_sync","");return v.isEmpty()?"Never":v;}
    public String lastResult(){return prefs.getString("cloud_last_result","Not connected");}
    public String backendStatus(){if(!backendConfigured())return "Not configured";return signedIn()?"Connected":"Configured · sign-in required";}
    public String workspaceAccessState(){return prefs.getString(KEY_WORKSPACE_ACCESS_STATE,ACCESS_UNKNOWN);}
    public String workspaceAccessCheckedAt(){String v=prefs.getString(KEY_WORKSPACE_ACCESS_CHECKED_AT,"");return v.isEmpty()?"Never":v;}
    public boolean workspaceAccessRevoked(String workspaceId){String id=prefs.getString(KEY_WORKSPACE_ACCESS_ID,"");return workspaceId!=null&&!workspaceId.isEmpty()&&workspaceId.equals(id)&&ACCESS_REVOKED.equals(prefs.getString(KEY_WORKSPACE_ACCESS_STATE,ACCESS_UNKNOWN));}
    private void markWorkspaceAccess(String workspaceId,String state){prefs.edit().putString(KEY_WORKSPACE_ACCESS_ID,workspaceId==null?"":workspaceId).putString(KEY_WORKSPACE_ACCESS_STATE,state==null?ACCESS_UNKNOWN:state).putString(KEY_WORKSPACE_ACCESS_CHECKED_AT,db.now()).apply();}

    public SupabaseClientLite.AuthResult signUp(String name,String email,String password)throws Exception{return client.signUp(name,email,password);}
    public SupabaseClientLite.AuthResult signIn(String email,String password)throws Exception{return client.signIn(email,password);}
    public WorkspaceMembership registerInvitedUser(String token,String name,String password)throws Exception{
        Object raw=client.invokePublicFunction("register-invited-user",new JSONObject().put("token",token==null?"":token.trim()).put("name",name==null?"":name.trim()).put("password",password));
        if(!(raw instanceof JSONObject))throw new Exception("Invitation registration returned an unexpected response");
        JSONObject o=(JSONObject)raw;if(!o.optBoolean("ok",false))throw new Exception(o.optString("message","Could not create invited account"));
        String email=o.optString("email","");if(email.isEmpty())throw new Exception("Invitation email was not returned");
        client.signIn(email,password);
        return new WorkspaceMembership(o.optString("workspace_id",""),o.optString("workspace_name","Workspace"),AccountTeamManager.normalizeRole(o.optString("role","technician")));
    }
    public void signOut()throws Exception{client.signOut();}

    public WorkspaceMembership firstWorkspace()throws Exception{
        Object raw=client.rpc("list_my_workspaces",new JSONObject());
        if(!(raw instanceof JSONArray)||((JSONArray)raw).length()==0)return null;
        JSONArray a=(JSONArray)raw;String preferred=prefs.getString(AccountTeamManager.KEY_WORKSPACE_ID,"");JSONObject chosen=null;
        for(int i=0;i<a.length();i++){JSONObject o=a.getJSONObject(i);if(preferred.equals(o.optString("workspace_id"))){chosen=o;break;}}
        if(chosen==null)chosen=a.getJSONObject(0);
        WorkspaceMembership m=new WorkspaceMembership(chosen.optString("workspace_id"),chosen.optString("workspace_name"),AccountTeamManager.normalizeRole(chosen.optString("role")));markWorkspaceAccess(m.id,ACCESS_ACTIVE);return m;
    }

    public WorkspaceMembership membershipForWorkspace(String workspaceId)throws Exception{
        if(workspaceId==null||workspaceId.trim().isEmpty())return null;Object raw=client.rpc("list_my_workspaces",new JSONObject());if(!(raw instanceof JSONArray))return null;JSONArray a=(JSONArray)raw;
        for(int i=0;i<a.length();i++){JSONObject o=a.getJSONObject(i);if(workspaceId.equals(o.optString("workspace_id"))){WorkspaceMembership m=new WorkspaceMembership(o.optString("workspace_id"),o.optString("workspace_name"),AccountTeamManager.normalizeRole(o.optString("role")));markWorkspaceAccess(workspaceId,ACCESS_ACTIVE);return m;}}return null;
    }

    public WorkspaceMembership refreshWorkspaceAccess(String workspaceId)throws Exception{
        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");WorkspaceMembership m=membershipForWorkspace(workspaceId);
        if(m==null){markWorkspaceAccess(workspaceId,ACCESS_REVOKED);markSyncResult(false,db.now(),"Workspace access disabled or removed");return null;}
        prefs.edit().putString(AccountTeamManager.KEY_WORKSPACE_NAME,m.name).putString(AccountTeamManager.KEY_ACCOUNT_ROLE,m.role).putBoolean(AccountTeamManager.KEY_CLOUD_WORKSPACE_BOUND,true).apply();return m;
    }

    public WorkspaceMembership createWorkspace(String name)throws Exception{
        Object raw=client.rpc("create_workspace",new JSONObject().put("p_name",name));String id=rpcString(raw);if(id.isEmpty())throw new Exception("Workspace was created but no ID was returned");return new WorkspaceMembership(id,name,AccountTeamManager.ROLE_OWNER);
    }

    public WorkspaceMembership acceptInvite(String token)throws Exception{
        Object raw=client.rpc("accept_workspace_invite",new JSONObject().put("p_token",token.trim()));String id=rpcString(raw);if(id.isEmpty())throw new Exception("Invitation could not be accepted");
        WorkspaceMembership m=firstWorkspace();if(m!=null&&id.equals(m.id))return m;
        JSONArray w=client.select("workspaces","select=id,name&id=eq."+id);String name=w.length()>0?w.getJSONObject(0).optString("name","Workspace"):"Workspace";return new WorkspaceMembership(id,name,AccountTeamManager.ROLE_TECHNICIAN);
    }

    public String createInvite(String workspaceId,String email,String role)throws Exception{
        JSONObject b=new JSONObject().put("p_workspace_id",workspaceId).put("p_email",email).put("p_role",role.toLowerCase());
        String token=rpcString(client.rpc("create_workspace_invite",b));
        boolean sent=false;String message="Invitation created. Share the code manually if email delivery is unavailable.";
        try{JSONObject delivery=sendInviteEmail(token);sent=delivery.optBoolean("sent",false);message=delivery.optString("message",message);}catch(Exception e){message="Invitation created, but email delivery failed: "+e.getMessage();}
        prefs.edit().putBoolean("cloud_last_invite_email_sent",sent).putString("cloud_last_invite_email_message",message).apply();
        return token;
    }

    private String operationalGenerationKey(String workspaceId){return "workspace_operational_generation_"+(workspaceId==null?"":workspaceId.trim());}
    private long rpcLong(Object raw){if(raw==null)return 0;if(raw instanceof Number)return ((Number)raw).longValue();if(raw instanceof JSONArray&&((JSONArray)raw).length()>0)return ((JSONArray)raw).optLong(0,0);try{return Long.parseLong(String.valueOf(raw).replace("\"","").trim());}catch(Exception e){return 0;}}
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

    private String serviceTypesCacheKey(String workspaceId){return "service_types_json_"+(workspaceId==null||workspaceId.trim().isEmpty()?"local":workspaceId.trim());}
    private String serviceTypesDirtyKey(String workspaceId){return "service_types_dirty_"+(workspaceId==null||workspaceId.trim().isEmpty()?"local":workspaceId.trim());}

    public JSONArray cachedServiceTypes(String workspaceId){
        String raw=prefs.getString(serviceTypesCacheKey(workspaceId),"");if(raw==null||raw.trim().isEmpty())return new JSONArray();
        try{return new JSONArray(raw);}catch(Exception ignored){return new JSONArray();}
    }

    public void cacheServiceTypes(String workspaceId,JSONArray types,boolean dirty){
        prefs.edit().putString(serviceTypesCacheKey(workspaceId),types==null?"[]":types.toString()).putBoolean(serviceTypesDirtyKey(workspaceId),dirty).apply();
    }

    public void syncServiceTypes(String workspaceId,boolean canManage)throws Exception{
        if(workspaceId==null||workspaceId.trim().isEmpty()||!backendConfigured()||!signedIn())return;
        String wid=workspaceId.trim();
        if(canManage&&prefs.getBoolean(serviceTypesDirtyKey(wid),false)){
            JSONArray local=cachedServiceTypes(wid);JSONArray cloud=client.select("service_checklist_templates","select=id,template_key&workspace_id=eq."+wid);java.util.HashSet<String> keep=new java.util.HashSet<>();
            for(int i=0;i<local.length();i++){JSONObject o=local.optJSONObject(i);if(o==null)continue;String key=o.optString("template_key","").trim();if(key.isEmpty())key="custom-"+UUID.randomUUID();keep.add(key);JSONArray items=o.optJSONArray("items");if(items==null)items=new JSONArray();JSONObject body=new JSONObject().put("workspace_id",wid).put("template_key",key).put("name",o.optString("name","Service type")).put("items",items).put("sort_order",(i+1)*10).put("active",true).put("updated_by",userId()).put("updated_at",isoNow());client.upsert("service_checklist_templates","workspace_id,template_key",body);}
            for(int i=0;i<cloud.length();i++){JSONObject o=cloud.optJSONObject(i);if(o==null)continue;String key=o.optString("template_key","");if(!keep.contains(key)){String id=o.optString("id","");if(!id.isEmpty())client.update("service_checklist_templates","id=eq."+id,new JSONObject().put("active",false).put("updated_by",userId()).put("updated_at",isoNow()));}}
            prefs.edit().putBoolean(serviceTypesDirtyKey(wid),false).apply();
        }
        JSONArray rows=client.select("service_checklist_templates","select=template_key,name,items,sort_order,active&workspace_id=eq."+wid+"&active=eq.true&order=sort_order.asc,name.asc");
        if(rows.length()>0)cacheServiceTypes(wid,rows,false);
    }

    public JSONObject aiReportDraft(String workspaceId,String title,String problem,String diagnosis,String workDone,String parts)throws Exception{
        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.trim().isEmpty())throw new Exception("Cloud workspace is not bound");
        JSONObject body=new JSONObject().put("workspace_id",workspaceId).put("title",title==null?"":title).put("problem",problem==null?"":problem).put("diagnosis",diagnosis==null?"":diagnosis).put("work_done",workDone==null?"":workDone).put("parts",parts==null?"":parts);
        Object raw=client.invokeFunction("ai-report-assistant",body);if(!(raw instanceof JSONObject))throw new Exception("AI report assistant returned an unexpected response");JSONObject o=(JSONObject)raw;if(!o.optBoolean("ok",false))throw new Exception(o.optString("message","AI report assistant failed"));JSONObject draft=o.optJSONObject("draft");if(draft==null)throw new Exception("AI report assistant returned no draft");return draft;
    }

    public JSONObject aiUsage(String workspaceId)throws Exception{
        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.trim().isEmpty())throw new Exception("Cloud workspace is not bound");
        Object raw=client.invokeFunction("ai-report-assistant",new JSONObject().put("workspace_id",workspaceId).put("action","usage"));if(!(raw instanceof JSONObject))throw new Exception("AI usage service returned an unexpected response");JSONObject o=(JSONObject)raw;if(!o.optBoolean("ok",false))throw new Exception(o.optString("message","Could not load AI usage"));JSONObject usage=o.optJSONObject("usage");if(usage==null)throw new Exception("AI usage data was not returned");return usage;
    }

    public JSONObject sendInviteEmail(String token)throws Exception{
        Object raw=client.invokeFunction("send-workspace-invite",new JSONObject().put("token",token==null?"":token.trim()));
        if(raw instanceof JSONObject)return (JSONObject)raw;
        return new JSONObject().put("sent",false).put("message","Invitation email service returned an unexpected response");
    }

    public boolean lastInviteEmailSent(){return prefs.getBoolean("cloud_last_invite_email_sent",false);}
    public String lastInviteEmailMessage(){return prefs.getString("cloud_last_invite_email_message","Invitation created");}
    public void cancelInvite(String inviteId)throws Exception{client.rpc("cancel_workspace_invite",new JSONObject().put("p_invite_id",inviteId));}
    public void clearCancelledInvites(String workspaceId)throws Exception{client.rpc("clear_cancelled_workspace_invites",new JSONObject().put("p_workspace_id",workspaceId));}
    public void updateMember(String workspaceId,String memberId,String role,String status)throws Exception{
        client.rpc("update_workspace_member",new JSONObject().put("p_workspace_id",workspaceId).put("p_member_id",memberId).put("p_role",role.toLowerCase()).put("p_status",status.toLowerCase()));
    }

    public void removeWorkspacePerson(String workspaceId,String memberId)throws Exception{
        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.trim().isEmpty())throw new Exception("Cloud workspace is not bound");if(memberId==null||memberId.trim().isEmpty())throw new Exception("Workspace member ID is missing");
        client.rpc("remove_workspace_person",new JSONObject().put("p_workspace_id",workspaceId.trim()).put("p_member_id",memberId.trim()));
    }

    public void refreshTeamCache(String workspaceId,boolean canManage)throws Exception{
        Object membersRaw=client.rpc("list_workspace_members",new JSONObject().put("p_workspace_id",workspaceId));JSONArray members=membersRaw instanceof JSONArray?(JSONArray)membersRaw:new JSONArray();JSONArray invites=new JSONArray();
        if(canManage){Object invitesRaw=client.rpc("list_workspace_invites",new JSONObject().put("p_workspace_id",workspaceId));if(invitesRaw instanceof JSONArray)invites=(JSONArray)invitesRaw;}
        db.cacheWorkspaceTeam(workspaceId,members,invites);
    }

    public SyncResult syncNow(String workspaceId,boolean canManage)throws Exception{
        synchronized(SYNC_LOCK){
            if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.isEmpty())throw new Exception("Cloud workspace is not bound");
            WorkspaceMembership verified=refreshWorkspaceAccess(workspaceId);if(verified==null)throw new Exception("Workspace access is disabled or has been removed. Ask the workspace Owner/Admin to re-enable your account, then check access again.");canManage=AccountTeamManager.ROLE_OWNER.equals(verified.role)||AccountTeamManager.ROLE_ADMIN.equals(verified.role);alignOperationalGeneration(workspaceId);
            int repaired=db.cleanupOrphanSyncState();
            int pushed=0,pulled=0,deferred=0;if(!canManage)db.discardManagerOnlyPendingChanges();String[] pushOrder=canManage?new String[]{"customer","site","asset","technician","job"}:new String[]{"job"};String[] deleteOrder=canManage?new String[]{"job","asset","site","customer","technician"}:new String[]{"job"};List<AppDatabase.Row> pending=db.pendingBusinessSyncRows();java.util.ArrayList<Long> finalizeCompleted=new java.util.ArrayList<>();java.util.HashSet<String> visibleJobIds=new java.util.HashSet<>();
            for(String type:deleteOrder){for(AppDatabase.Row q:pending){if(!type.equals(q.s("entity_type"))||!"delete".equals(q.s("operation")))continue;long localId=parseLong(q.s("entity_id"));if(localId<=0)continue;String remote=q.s("remote_uuid");if(remote.isEmpty()){db.markDeletionSynced(type,localId,"");continue;}client.update(tableFor(type),"id=eq."+remote+"&workspace_id=eq."+workspaceId,new JSONObject().put("deleted_at",isoNow()));db.markDeletionSynced(type,localId,remote);pushed++;}}
            for(String type:pushOrder){for(AppDatabase.Row q:pending){if(!type.equals(q.s("entity_type"))||"delete".equals(q.s("operation")))continue;long localId=parseLong(q.s("entity_id"));if(localId<=0)continue;if("job".equals(type)&&!db.hasEverSynced("job",localId))reserveReportNumberForFirstSync(localId,workspaceId);JSONObject body=payload(type,localId,workspaceId);if(body==null)continue;String remoteId=body.optString("id");if("technician".equals(type)){String canonical=canonicalTechnicianRemoteId(workspaceId,body);if(!canonical.isEmpty()&&!canonical.equals(remoteId)){long mappedLocal=db.localIdForRemote("technician",canonical);if(mappedLocal>0&&mappedLocal!=localId)localId=db.reconcileTechnicianIdentity(localId,mappedLocal,canonical);else db.bindRemoteUuid("technician",localId,canonical);body.put("id",canonical);remoteId=canonical;}}if("job".equals(type)&&!canManage&&"Completed".equals(body.optString("status"))){JSONObject staged=new JSONObject(body.toString());staged.put("status","In Progress");client.upsert(tableFor(type),"id",staged);db.bindRemoteUuid(type,localId,remoteId);finalizeCompleted.add(localId);}else{client.upsert(tableFor(type),"id",body);db.markEntitySynced(type,localId,remoteId);}pushed++;}}
            for(String type:pushOrder){JSONArray rows=client.select(tableFor(type),"select=*&workspace_id=eq."+workspaceId);for(int i=0;i<rows.length();i++){JSONObject o=rows.getJSONObject(i);String remote=o.optString("id","");if(remote.isEmpty())continue;if("job".equals(type))visibleJobIds.add(remote);if(isDeleted(o)){long before=db.localIdForRemote(type,remote);if(before>0&&!db.applyRemoteDeletion(type,remote)){deferred++;continue;}if(before>0)pulled++;continue;}long local=db.localIdForRemote(type,remote);if(local>0&&db.hasPendingSync(type,local)){db.recordSyncConflict(type,local,remote,"Cloud update deferred because this device has unsynced edits");deferred++;continue;}long saved=db.upsertRemoteEntity(type,o);if(saved>0)pulled++;}}
            if(!canManage)db.pruneInvisibleCloudJobs(visibleJobIds);
            syncCustomerSites(workspaceId,canManage);
            syncBranding(workspaceId,canManage);
            syncServiceTypes(workspaceId,canManage);
            CloudMediaSync.Result media=new CloudMediaSync(context,prefs,db,client).sync(workspaceId,canManage);
            for(Long localId:finalizeCompleted){JSONObject finalBody=payload("job",localId,workspaceId);if(finalBody!=null){client.upsert("jobs","id",finalBody);db.markEntitySynced("job",localId,finalBody.optString("id"));}}
            syncAssignmentHistory(workspaceId);
            refreshTeamCache(workspaceId,canManage);
            repaired+=db.cleanupOrphanSyncState();
            int pushedTotal=pushed+media.recordsPushed,pulledTotal=pulled+media.recordsPulled;long conflicts=db.unresolvedConflictCount();
            String status="Success · "+pushedTotal+" pushed, "+pulledTotal+" received · "+media.filesUploaded+" file upload"+(media.filesUploaded==1?"":"s")+", "+media.filesDownloaded+" download"+(media.filesDownloaded==1?"":"s")+(conflicts>0?" · "+conflicts+" protected conflict"+(conflicts==1?"":"s"):"")+(repaired>0?" · "+repaired+" stale sync item"+(repaired==1?"":"s")+" repaired":"");markSyncResult(true,db.now(),status);prefs.edit().putLong("cloud_last_conflicts",conflicts).apply();
            String message="Synced "+pushedTotal+" local record"+(pushedTotal==1?"":"s")+", received "+pulledTotal+" cloud record"+(pulledTotal==1?"":"s")+" and synchronized "+(media.filesUploaded+media.filesDownloaded)+" media file"+((media.filesUploaded+media.filesDownloaded)==1?"":"s")+(deferred>0?". "+deferred+" cloud change"+(deferred==1?" was":"s were")+" deferred to protect unsynced local work.":".")+(repaired>0?" Repaired "+repaired+" stale sync item"+(repaired==1?".":"s."):"");return new SyncResult(pushedTotal,pulledTotal,message);
        }
    }

    private void reserveReportNumberForFirstSync(long localId,String workspaceId)throws Exception{
        if(localId<=0||db.hasEverSynced("job",localId))return;AppDatabase.Row job=db.syncEntity("job",localId);if(job.id()==0)return;String requested=job.s("report_no");String remoteId=db.ensureRemoteUuid("job",localId);long localMax=db.maxLocalReportSequence(requested);
        Object raw=client.rpc("reserve_report_number",new JSONObject().put("p_workspace_id",workspaceId).put("p_job_id",remoteId).put("p_requested_report_no",requested).put("p_local_max_seq",localMax));String reserved=rpcString(raw);
        if(reserved.isEmpty())throw new Exception("Could not reserve a workspace report number");if(!reserved.equalsIgnoreCase(requested))db.updateJobReportNoFromCloud(localId,reserved);
    }

    private String canonicalTechnicianRemoteId(String workspaceId,JSONObject body)throws Exception{
        if(body==null||body.isNull("user_id"))return "";String user=body.optString("user_id","").trim();if(user.isEmpty())return "";JSONArray rows=client.select("technicians","select=id&workspace_id=eq."+workspaceId+"&user_id=eq."+user+"&deleted_at=is.null&limit=1");return rows.length()>0?rows.getJSONObject(0).optString("id",""):"";
    }

    private void syncAssignmentHistory(String workspaceId)throws Exception{JSONArray history=client.select("job_assignment_history","select=*&workspace_id=eq."+workspaceId+"&order=changed_at.asc");db.cacheAssignmentHistory(history);}

    private void syncBranding(String workspaceId,boolean canManage)throws Exception{
        JSONArray remote=client.select("branding_settings","select=enabled,primary_color,accent_color,highlight_color&workspace_id=eq."+workspaceId);boolean dirty=prefs.getBoolean(BrandingManager.KEY_SETTINGS_DIRTY,false);boolean localCustom=prefs.getBoolean(BrandingManager.KEY_ENABLED,false);
        boolean remoteDefault=remote.length()==0||(!remote.getJSONObject(0).optBoolean("enabled",false)&&"#464B45".equalsIgnoreCase(remote.getJSONObject(0).optString("primary_color","#464B45"))&&"#F99D1C".equalsIgnoreCase(remote.getJSONObject(0).optString("accent_color","#F99D1C"))&&"#FFC222".equalsIgnoreCase(remote.getJSONObject(0).optString("highlight_color","#FFC222")));
        if(canManage&&(dirty||remote.length()==0||(localCustom&&remoteDefault))){JSONObject b=new JSONObject().put("workspace_id",workspaceId).put("enabled",prefs.getBoolean(BrandingManager.KEY_ENABLED,false)).put("primary_color",prefs.getString(BrandingManager.KEY_PRIMARY,"#464B45")).put("accent_color",prefs.getString(BrandingManager.KEY_ACCENT,"#F99D1C")).put("highlight_color",prefs.getString(BrandingManager.KEY_HIGHLIGHT,"#FFC222"));client.upsert("branding_settings","workspace_id",b);prefs.edit().putBoolean(BrandingManager.KEY_SETTINGS_DIRTY,false).apply();remote=client.select("branding_settings","select=enabled,primary_color,accent_color,highlight_color&workspace_id=eq."+workspaceId);}
        if(remote.length()>0){JSONObject o=remote.getJSONObject(0);prefs.edit().putBoolean(BrandingManager.KEY_ENABLED,o.optBoolean("enabled",false)).putString(BrandingManager.KEY_PRIMARY,o.optString("primary_color","#464B45")).putString(BrandingManager.KEY_ACCENT,o.optString("accent_color","#F99D1C")).putString(BrandingManager.KEY_HIGHLIGHT,o.optString("highlight_color","#FFC222")).putBoolean(BrandingManager.KEY_SETTINGS_DIRTY,false).apply();}
    }

    private JSONObject payload(String type,long id,String workspaceId)throws Exception{
        AppDatabase.Row r=db.syncEntity(type,id);if(r.id()==0)return null;String remote=db.ensureRemoteUuid(type,id);JSONObject o=new JSONObject().put("id",remote).put("workspace_id",workspaceId).put("deleted_at",JSONObject.NULL);
        if("customer".equals(type)){copy(o,r,"name","contact","phone","email","address","notes");}
        else if("site".equals(type)){copy(o,r,"name","address","contact","phone","notes");putRemoteRef(o,"customer_id","customer",r.s("customer_id"));}
        else if("asset".equals(type)){copy(o,r,"tag","name","category","make_model","serial","location","notes");o.put("interval_days",r.i("interval_days"));putDate(o,"next_service",r.s("next_service"));putRemoteRef(o,"customer_id","customer",r.s("customer_id"));putRemoteRef(o,"site_id","site",r.s("site_id"));}
        else if("technician".equals(type)){copy(o,r,"name","role","phone","email");String user=r.s("user_uuid");if(user.isEmpty())o.put("user_id",JSONObject.NULL);else o.put("user_id",user);o.put("active",r.i("active")==1);}
        else if("job".equals(type)){copy(o,r,"report_no","title","problem","diagnosis","work_done","parts","priority","status","customer_name_signed");o.put("service_started_at_ms",r.l("service_started_at_ms"));o.put("service_completed_at_ms",r.l("service_completed_at_ms"));o.put("service_duration_minutes",r.i("service_duration_minutes"));o.put("service_sessions",db.jobServiceSessions(r.id()));o.put("technician_name",r.s("technician"));putRemoteRef(o,"technician_id","technician",r.s("technician_id"));putDate(o,"job_date",r.s("job_date"));putDate(o,"next_service",r.s("next_service"));putRemoteRef(o,"customer_id","customer",r.s("customer_id"));putRemoteRef(o,"site_id","site",r.s("site_id"));putRemoteRef(o,"asset_id","asset",r.s("asset_id"));}
        else return null;return o;
    }

    private void copy(JSONObject o,AppDatabase.Row r,String... keys)throws Exception{for(String k:keys)o.put(k,r.s(k));}
    private void putDate(JSONObject o,String key,String value)throws Exception{if(value==null||value.trim().isEmpty())o.put(key,JSONObject.NULL);else o.put(key,value.trim());}
    private void putRemoteRef(JSONObject o,String key,String type,String local)throws Exception{long id=parseLong(local);if(id<=0)o.put(key,JSONObject.NULL);else o.put(key,db.ensureRemoteUuid(type,id));}
    private long parseLong(String value){try{return Long.parseLong(value==null?"0":value);}catch(Exception e){return 0;}}
    private boolean isDeleted(JSONObject o){return o!=null&&!o.isNull("deleted_at")&&!o.optString("deleted_at","").isEmpty();}
    private String isoNow(){return java.time.Instant.now().toString();}
    private String tableFor(String type){if("customer".equals(type))return "customers";if("site".equals(type))return "sites";if("asset".equals(type))return "assets";if("technician".equals(type))return "technicians";if("job".equals(type))return "jobs";return type;}
    private String rpcString(Object raw){if(raw==null)return "";if(raw instanceof String)return ((String)raw).replace("\"","").trim();if(raw instanceof JSONObject)return ((JSONObject)raw).optString("result","");if(raw instanceof JSONArray&&((JSONArray)raw).length()>0)return ((JSONArray)raw).optString(0,"");return String.valueOf(raw).replace("\"","").trim();}
    public void markSyncResult(boolean ok,String when,String message){prefs.edit().putString("cloud_last_sync",when==null?"":when).putString("cloud_last_result",message==null?(ok?"Success":"Failed"):message).apply();}
}
