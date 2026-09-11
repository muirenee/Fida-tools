from pathlib import Path
import re

# Cloud invitation email call
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
s=p.read_text()
anchor='''    public String createInvite(String workspaceId,String email,String role)throws Exception{\n        JSONObject b=new JSONObject().put("p_workspace_id",workspaceId).put("p_email",email).put("p_role",role.toLowerCase());return rpcString(client.rpc("create_workspace_invite",b));\n    }'''
assert anchor in s, 'createInvite anchor not found'
replacement=anchor+'''\n\n    public JSONObject sendInviteEmail(String token)throws Exception{\n        Object raw=client.invokeFunction("send-workspace-invite",new JSONObject().put("token",token==null?"":token.trim()));\n        if(raw instanceof JSONObject)return (JSONObject)raw;\n        return new JSONObject().put("sent",false).put("message","Invitation email service returned an unexpected response");\n    }'''
s=s.replace(anchor,replacement,1)
p.write_text(s)

# UI: create invitation + automatically send email, with manual-code fallback
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s=p.read_text()
pattern=re.compile(r'''    private void showInviteDialog\(\)\{showInviteDialog\("",AccountTeamManager\.ROLE_TECHNICIAN\);\}\n    private void showInviteDialog\(String prefillEmail,String defaultRole\)\{.*?\n    \}\n\n    private void showPeopleTeam\(\)\{''',re.S)
m=pattern.search(s)
assert m, 'showInviteDialog block not found'
new='''    private void showInviteDialog(){showInviteDialog("",AccountTeamManager.ROLE_TECHNICIAN);}\n    private void showInviteDialog(String prefillEmail,String defaultRole){\n        if(!accountTeam.canManageTeam()){toast("Owner or Admin access required");return;}\n        LinearLayout f=form();\n        EditText email=input("Email address",prefillEmail==null?"":prefillEmail);\n        Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});\n        setSpinner(role,defaultRole==null?AccountTeamManager.ROLE_TECHNICIAN:defaultRole);\n        f.addView(email);f.addView(label("Role"));f.addView(role);\n        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Invite workspace member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Send invitation",null).create();\n        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{\n            String e=val(email),r=String.valueOf(role.getSelectedItem());\n            if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}\n            if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){\n                runCloud("Creating and sending invitation…",()->{\n                    String token=cloudSync.createInvite(accountTeam.workspaceId(),e,r);\n                    JSONObject delivery=cloudSync.sendInviteEmail(token);\n                    cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);\n                    return new JSONObject().put("token",token).put("sent",delivery.optBoolean("sent",false)).put("delivery_message",delivery.optString("message",""));\n                },obj->{\n                    d.dismiss();\n                    JSONObject result=(JSONObject)obj;String token=result.optString("token","");boolean sent=result.optBoolean("sent",false);String delivery=result.optString("delivery_message","");\n                    String message=sent?("Invitation email sent to "+e+". The recipient can sign in or create an account with that email and use the included invitation code."):("The workspace invitation was created, but the email was not sent automatically.\\n\\n"+(delivery.isEmpty()?"Email delivery is not configured.":delivery)+"\\n\\nInvitation code:\\n"+token);\n                    MaterialAlertDialogBuilder done=new MaterialAlertDialogBuilder(this).setTitle(sent?"Invitation sent":"Invitation created").setMessage(message).setNegativeButton("Close",(a,b)->showPeopleTeam());\n                    if(!token.isEmpty())done.setNeutralButton("Copy code",(a,b)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",token));toast("Invitation code copied");showPeopleTeam();});\n                    if(!sent&&!token.isEmpty())done.setPositiveButton("Retry email",(a,b)->retryInviteEmail(token,e));\n                    done.show();\n                });\n            }else{db.saveWorkspaceInvite(accountTeam.workspaceId(),e,r);d.dismiss();toast("Invitation saved locally. Connect this workspace to cloud sync to send email invitations.");showPeopleTeam();}\n        }));\n        d.show();\n    }\n\n    private void retryInviteEmail(String token,String email){\n        runCloud("Sending invitation email…",()->cloudSync.sendInviteEmail(token),obj->{JSONObject delivery=(JSONObject)obj;boolean sent=delivery.optBoolean("sent",false);if(sent)toast("Invitation email sent to "+email);else new MaterialAlertDialogBuilder(this).setTitle("Email not sent").setMessage(delivery.optString("message","Email delivery failed. You can still share the invitation code manually.")).setPositiveButton("OK",null).show();showPeopleTeam();});\n    }\n\n    private void showPeopleTeam(){'''
s=s[:m.start()]+new+s[m.end():]
s=s.replace('Fida Field 0.9.15 Test\\nAssignment-scoped service jobs, reassignment history and secure workspace access by Fidalix.','Fida Field 0.9.16 Test\\nEmail workspace invitations, assignment-scoped service jobs and secure cloud teamwork by Fidalix.',1)
# If the exact 0.9.15 about text differs, replace the visible version at least.
s=s.replace('Fida Field 0.9.15 Test','Fida Field 0.9.16 Test',1)
p.write_text(s)

# Version bump
p=Path('fida-field/app/build.gradle')
s=p.read_text()
assert 'versionCode 18' in s and "versionName '0.9.15-test'" in s, '0.9.15 version anchors not found'
s=s.replace('versionCode 18','versionCode 19',1).replace("versionName '0.9.15-test'","versionName '0.9.16-test'",1)
p.write_text(s)
