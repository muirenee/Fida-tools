from pathlib import Path

# Cloud invitation creation now automatically attempts secure backend email delivery.
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s=p.read_text()
anchor='''    public String createInvite(String workspaceId,String email,String role)throws Exception{\n        JSONObject b=new JSONObject().put("p_workspace_id",workspaceId).put("p_email",email).put("p_role",role.toLowerCase());return rpcString(client.rpc("create_workspace_invite",b));\n    }'''
assert anchor in s, 'createInvite anchor not found'
replacement='''    public String createInvite(String workspaceId,String email,String role)throws Exception{\n        JSONObject b=new JSONObject().put("p_workspace_id",workspaceId).put("p_email",email).put("p_role",role.toLowerCase());\n        String token=rpcString(client.rpc("create_workspace_invite",b));\n        boolean sent=false;String message="Invitation created. Share the code manually if email delivery is unavailable.";\n        try{JSONObject delivery=sendInviteEmail(token);sent=delivery.optBoolean("sent",false);message=delivery.optString("message",message);}catch(Exception e){message="Invitation created, but email delivery failed: "+e.getMessage();}\n        prefs.edit().putBoolean("cloud_last_invite_email_sent",sent).putString("cloud_last_invite_email_message",message).apply();\n        return token;\n    }\n\n    public JSONObject sendInviteEmail(String token)throws Exception{\n        Object raw=client.invokeFunction("send-workspace-invite",new JSONObject().put("token",token==null?"":token.trim()));\n        if(raw instanceof JSONObject)return (JSONObject)raw;\n        return new JSONObject().put("sent",false).put("message","Invitation email service returned an unexpected response");\n    }\n\n    public boolean lastInviteEmailSent(){return prefs.getBoolean("cloud_last_invite_email_sent",false);}\n    public String lastInviteEmailMessage(){return prefs.getString("cloud_last_invite_email_message","Invitation created");}'''
s=s.replace(anchor,replacement,1)
p.write_text(s)

# Keep the existing invitation UI/flow intact; only surface backend email-delivery result.
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s=p.read_text()
old='d.dismiss();String token=String.valueOf(obj);new MaterialAlertDialogBuilder(this).setTitle("Invitation created")'
new='d.dismiss();String token=String.valueOf(obj);toast(cloudSync.lastInviteEmailMessage());new MaterialAlertDialogBuilder(this).setTitle(cloudSync.lastInviteEmailSent()?"Invitation sent":"Invitation created")'
assert old in s, 'invitation success UI anchor not found'
s=s.replace(old,new,1)
s=s.replace('Fida Field 0.9.15 Test','Fida Field 0.9.16 Test',1)
p.write_text(s)

# Version bump
p=Path('fida-field/app/build.gradle')
s=p.read_text()
assert 'versionCode 18' in s and "versionName '0.9.15-test'" in s, '0.9.15 version anchors not found'
s=s.replace('versionCode 18','versionCode 19',1).replace("versionName '0.9.15-test'","versionName '0.9.16-test'",1)
p.write_text(s)
