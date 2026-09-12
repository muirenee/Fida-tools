from pathlib import Path
p=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s=p.read_text()
needle='        b.addView(section("Current plan"));b.addView(info("Plan",entitlements.planName()));b.addView(info("Entitlement",entitlements.entitlementSource()));b.addView(info("Subscription scope",BuildConfig.OPEN_EDITION?"Internal Fidalix build":"Company / workspace"));b.addView(info("Monthly usage",entitlements.usageSummary()));\n'
extra='''        if(cloudSync!=null&&accountTeam!=null&&cloudSync.signedIn()&&accountTeam.hasCloudWorkspace()&&accountTeam.canManageTeam()){\n            b.addView(section("AI report assistant"));TextView aiState=paragraph("Loading workspace AI allowance…");b.addView(aiState);MaterialButton aiRefresh=outlineButton("Refresh AI usage");aiRefresh.setOnClickListener(v->refreshAiUsage(aiState));b.addView(aiRefresh);refreshAiUsage(aiState);\n        }else if(entitlements.canUseAiReportAssistant()){\n            b.addView(section("AI report assistant"));b.addView(paragraph("AI report writing is available with this plan. Owner/Admin can view the workspace allowance after signing in to the cloud workspace."));\n        }\n'''
if 'Refresh AI usage' not in s:
    if needle not in s: raise SystemExit('0.9.29 plan anchor missing')
    s=s.replace(needle,needle+extra,1)
anchor='    private void showBranding(){\n'
helper='''    private void refreshAiUsage(TextView host){\n        if(host==null||cloudSync==null||accountTeam==null||!cloudSync.signedIn()||!accountTeam.hasCloudWorkspace()){if(host!=null)host.setText("Cloud workspace sign-in required.");return;}\n        host.setText("Refreshing workspace AI usage…");\n        new Thread(()->{try{JSONObject u=cloudSync.aiUsage(accountTeam.workspaceId());int used=u.optInt("used_this_month",0),limit=u.optInt("monthly_limit",0),remaining=u.optInt("remaining",0);boolean enabled=u.optBoolean("enabled",false),entitled=u.optBoolean("entitled",false);String period=u.optString("period_start","")+" → "+u.optString("period_end","");String msg=(enabled?"Service enabled":"Service paused")+" · "+(entitled?"Workspace entitled":"No active AI entitlement")+"\\nThis month: "+used+" / "+limit+" assists · "+remaining+" remaining"+(period.trim().equals("→")?"":"\\nPeriod: "+period);runOnUiThread(()->host.setText(msg));}catch(Exception e){String msg=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();runOnUiThread(()->host.setText("AI usage unavailable: "+msg));}}).start();\n    }\n\n'''
if 'private void refreshAiUsage(' not in s:
    if anchor not in s: raise SystemExit('0.9.29 helper anchor missing')
    s=s.replace(anchor,helper+anchor,1)
s=s.replace('Pro unlocks unlimited reports, CSV exports and custom company branding.','Pro unlocks unlimited reports, CSV exports, custom company branding and the AI report assistant.',1)
p.write_text(s)
print('0.9.29 UI applied')
