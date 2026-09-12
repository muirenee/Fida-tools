from pathlib import Path
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s=p.read_text()
anchor='    public JSONObject sendInviteEmail(String token)throws Exception{\n'
method='''    public JSONObject aiUsage(String workspaceId)throws Exception{\n        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.trim().isEmpty())throw new Exception("Cloud workspace is not bound");\n        Object raw=client.invokeFunction("ai-report-assistant",new JSONObject().put("workspace_id",workspaceId).put("action","usage"));if(!(raw instanceof JSONObject))throw new Exception("AI usage service returned an unexpected response");JSONObject o=(JSONObject)raw;if(!o.optBoolean("ok",false))throw new Exception(o.optString("message","Could not load AI usage"));JSONObject usage=o.optJSONObject("usage");if(usage==null)throw new Exception("AI usage data was not returned");return usage;\n    }\n\n'''
if 'public JSONObject aiUsage(' not in s:
    if anchor not in s: raise SystemExit('0.9.29 cloud anchor missing')
    s=s.replace(anchor,method+anchor,1)
p.write_text(s)
print('0.9.29 cloud helper applied')
