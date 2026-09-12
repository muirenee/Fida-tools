from pathlib import Path

root = Path('fida-field/app/src/main/java/com/fidalix/fidafield')
main_path = root / 'MainActivity.java'
cloud_path = root / 'CloudSyncFoundation.java'
ent_path = root / 'EntitlementManager.java'
gradle_path = Path('fida-field/app/build.gradle')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'0.9.28 patch failed: {label} pattern not found')
    return text.replace(old, new, 1)

# Commercial entitlement: AI report writing is Pro/Open edition.
s = ent_path.read_text()
s = replace_once(
    s,
    '    public boolean canExportCsv() { return isPro(); }\n    public boolean canUseCustomBranding() { return isPro(); }\n',
    '    public boolean canExportCsv() { return isPro(); }\n    public boolean canUseCustomBranding() { return isPro(); }\n    public boolean canUseAiReportAssistant() { return isPro(); }\n',
    'AI entitlement'
)
ent_path.write_text(s)

# Cloud client wrapper for the authenticated Supabase Edge Function.
s = cloud_path.read_text()
anchor = '    public JSONObject sendInviteEmail(String token)throws Exception{\n'
method = '''    public JSONObject aiReportDraft(String workspaceId,String title,String problem,String diagnosis,String workDone,String parts)throws Exception{\n        if(!backendConfigured())throw new Exception("Supabase backend is not configured");if(!signedIn())throw new Exception("Please sign in first");if(workspaceId==null||workspaceId.trim().isEmpty())throw new Exception("Cloud workspace is not bound");\n        JSONObject body=new JSONObject().put("workspace_id",workspaceId).put("title",title==null?"":title).put("problem",problem==null?"":problem).put("diagnosis",diagnosis==null?"":diagnosis).put("work_done",workDone==null?"":workDone).put("parts",parts==null?"":parts);\n        Object raw=client.invokeFunction("ai-report-assistant",body);if(!(raw instanceof JSONObject))throw new Exception("AI report assistant returned an unexpected response");JSONObject o=(JSONObject)raw;if(!o.optBoolean("ok",false))throw new Exception(o.optString("message","AI report assistant failed"));JSONObject draft=o.optJSONObject("draft");if(draft==null)throw new Exception("AI report assistant returned no draft");return draft;\n    }\n\n'''
s = replace_once(s, anchor, method + anchor, 'AI cloud method')
cloud_path.write_text(s)

# Job editor UI and review-before-apply workflow.
s = main_path.read_text()
old_form = 'form.addView(jobTitle);form.addView(problem);form.addView(diagnosis);form.addView(work);form.addView(parts);form.addView(label("Technician"));form.addView(tech);'
new_form = 'form.addView(jobTitle);form.addView(problem);form.addView(diagnosis);form.addView(work);form.addView(parts);MaterialButton aiAssist=outlineButton("AI assist report");aiAssist.setOnClickListener(v->showAiReportAssistant(jobTitle,problem,diagnosis,work,parts));form.addView(aiAssist);form.addView(label("Technician"));form.addView(tech);'
s = replace_once(s, old_form, new_form, 'job editor AI button')

anchor = '    private void showJobDetail(long id){\n'
method = '''    private void showAiReportAssistant(EditText jobTitle,EditText problem,EditText diagnosis,EditText work,EditText parts){\n        if(!entitlements.canUseAiReportAssistant()){showUpgradeRequired("AI report assistant");return;}\n        if(accountTeam==null||!accountTeam.hasWorkspace()||!cloudSync.signedIn()){new MaterialAlertDialogBuilder(this).setTitle("Cloud sign-in required").setMessage("AI report assist uses the secure Fida Field cloud service. Sign in and connect a workspace first.").setNegativeButton("Cancel",null).setPositiveButton("Open account",(d,w)->showAccountWorkspace()).show();return;}\n        if(val(problem).isEmpty()&&val(diagnosis).isEmpty()&&val(work).isEmpty()&&val(parts).isEmpty()){toast("Enter some service notes first");return;}\n        toast("Preparing AI report suggestion…");new Thread(()->{try{JSONObject draft=cloudSync.aiReportDraft(accountTeam.workspaceId(),val(jobTitle),val(problem),val(diagnosis),val(work),val(parts));runOnUiThread(()->showAiReportDraftReview(diagnosis,work,parts,draft));}catch(Exception e){String msg=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();runOnUiThread(()->new MaterialAlertDialogBuilder(this).setTitle("AI assistant unavailable").setMessage(msg).setPositiveButton("OK",null).show());}}).start();\n    }\n\n    private void showAiReportDraftReview(EditText diagnosis,EditText work,EditText parts,JSONObject draft){\n        String d=draft.optString("diagnosis","").trim(),w=draft.optString("work_done","").trim(),p=draft.optString("parts","").trim();if(d.isEmpty())d=val(diagnosis);if(w.isEmpty())w=val(work);if(p.isEmpty())p=val(parts);\n        LinearLayout f=form();f.addView(paragraph("Review the suggestion before applying it. AI improves wording only; verify every technical fact."));EditText dEdit=multi("Diagnosis",d);EditText wEdit=multi("Work performed",w);EditText pEdit=multi("Parts / materials",p);f.addView(dEdit);f.addView(wEdit);f.addView(pEdit);\n        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle("AI report suggestion").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Apply",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{diagnosis.setText(val(dEdit));work.setText(val(wEdit));parts.setText(val(pEdit));dialog.dismiss();toast("AI wording applied · review before saving");}));dialog.show();\n    }\n\n'''
s = replace_once(s, anchor, method + anchor, 'AI UI methods')
main_path.write_text(s)

# Version bump.
g = gradle_path.read_text()
g = replace_once(g, '        versionCode 30\n', '        versionCode 31\n', 'version code')
g = replace_once(g, "        versionName '0.9.27-test'\n", "        versionName '0.9.28-test'\n", 'version name')
gradle_path.write_text(g)

print('Fida Field 0.9.28 AI report assistant applied')
