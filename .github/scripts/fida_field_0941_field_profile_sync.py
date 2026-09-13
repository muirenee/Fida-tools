from pathlib import Path

GRADLE=Path('fida-field/app/build.gradle')
CLOUD=Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
MAIN=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')


def replace_once(path, old, new):
    s=path.read_text()
    if old not in s:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:180]!r}')
    path.write_text(s.replace(old,new,1))

replace_once(GRADLE,
    "versionCode 43\n        versionName '0.9.40-test'",
    "versionCode 44\n        versionName '0.9.41-test'")

s=CLOUD.read_text()
old='int pushed=0,pulled=0,deferred=0;if(!canManage)db.discardManagerOnlyPendingChanges();String[] pushOrder=canManage?new String[]{"customer","site","asset","technician","job"}:new String[]{"job"};String[] deleteOrder=canManage?new String[]{"job","asset","site","customer","technician"}:new String[]{"job"};'
new='int pushed=0,pulled=0,deferred=0;if(!canManage)db.discardManagerOnlyPendingChanges();String[] pushOrder=canManage?new String[]{"customer","site","asset","technician","job"}:new String[]{"job"};String[] pullOrder=canManage?new String[]{"customer","site","asset","technician","job"}:new String[]{"technician","job"};String[] deleteOrder=canManage?new String[]{"job","asset","site","customer","technician"}:new String[]{"job"};'
if old not in s:
    raise SystemExit('Could not add separate pullOrder')
s=s.replace(old,new,1)
old='for(String type:pushOrder){JSONArray rows=client.select(tableFor(type),"select=*&workspace_id=eq."+workspaceId);'
new='for(String type:pullOrder){JSONArray rows=client.select(tableFor(type),"select=*&workspace_id=eq."+workspaceId);'
if old not in s:
    raise SystemExit('Could not switch cloud pull loop to pullOrder')
s=s.replace(old,new,1)
CLOUD.write_text(s)

replace_once(MAIN,
    'private long myTechnicianId(){AppDatabase.Row t=db.technicianForUser(currentJobUserUuid());return t.id();}',
    'private long myTechnicianId(){AppDatabase.Row t=db.technicianForUser(currentJobUserUuid());return t.id()>0&&t.i("active")==1?t.id():0;}')

print('Fida Field 0.9.41 field profile sync fix applied')
