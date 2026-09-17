from pathlib import Path

GRADLE=Path('fida-field/app/build.gradle')
MAIN=Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')


def replace_once(path:Path,old:str,new:str):
    text=path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:260]!r}')
    path.write_text(text.replace(old,new,1))

replace_once(GRADLE,"versionCode 51\n        versionName '0.9.48-test'","versionCode 52\n        versionName '0.9.49-test'")

# QA-discovered UX/permission issue: Viewer could see a create-job choice from Maintenance,
# even though the job dialog correctly rejected the action. Keep the action list itself role-correct.
replace_once(
    MAIN,
    '''    private void showMaintenanceAction(AppDatabase.Row asset){\n        if(canSeeAllJobs()){String[] actions={"Create service job","Mark serviced now","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else if(which==1)showQuickMaintenanceDialog(asset);else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}else{String[] actions={"Create my service job","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}\n    }\n''',
    '''    private void showMaintenanceAction(AppDatabase.Row asset){\n        if(canSeeAllJobs()){String[] actions={"Create service job","Mark serviced now","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else if(which==1)showQuickMaintenanceDialog(asset);else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}\n        else if(canPerformFieldWork()){String[] actions={"Create my service job","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}\n        else{String[] actions={"View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Read-only access · Next service: "+asset.s("next_service")).setItems(actions,(d,which)->showAssetDetail(asset.id())).setNegativeButton("Close",null).show();}\n    }\n'''
)

# Add an in-app QA snapshot so each test device can confirm identity, role boundaries and sync state.
replace_once(
    MAIN,
    '        b.addView(menuCard("Cloud & team sync",cloudSync.backendStatus()+" • "+cloudSync.pendingChanges()+" pending",v->showCloudSync()));\n',
    '        b.addView(menuCard("Cloud & team sync",cloudSync.backendStatus()+" • "+cloudSync.pendingChanges()+" pending",v->showCloudSync()));\n        b.addView(menuCard("Release readiness QA","Role permissions, device identity & multi-device sync checks",v->showReleaseReadiness()));\n'
)

qa_method=r'''    private String qaResult(boolean ok){return ok?"PASS":"CHECK";}

    private void showReleaseReadiness(){
        setHeader("Release readiness QA","Role & multi-device checks");mainTabScreen=false;clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        String role=accountTeam==null?"":accountTeam.accountRole();boolean hasWorkspace=accountTeam!=null&&accountTeam.hasWorkspace();boolean cloudWorkspace=accountTeam!=null&&accountTeam.hasCloudWorkspace();boolean owner=AccountTeamManager.ROLE_OWNER.equals(role),admin=AccountTeamManager.ROLE_ADMIN.equals(role),technician=AccountTeamManager.ROLE_TECHNICIAN.equals(role),viewer=AccountTeamManager.ROLE_VIEWER.equals(role);boolean manager=owner||admin;
        String device=cloudSync==null?"":cloudSync.deviceId();if(device.length()>12)device=device.substring(0,12)+"…";
        b.addView(heroCard("Device QA snapshot","Use this screen on each test phone to confirm that account role, field permissions and workspace synchronization match the expected behavior before 1.0."));
        b.addView(section("Identity"));b.addView(info("Device",device.isEmpty()?"Not initialized":device));b.addView(info("Account",cloudSync!=null&&!cloudSync.accountEmail().isEmpty()?cloudSync.accountEmail():"Local / not signed in"));b.addView(info("Workspace",hasWorkspace?accountTeam.workspaceName():"Local mode"));b.addView(info("Role",role.isEmpty()?"Local user":role));b.addView(info("Workspace access",workspaceAccessRevoked()?"Disabled":cloudSync.workspaceAccessState()));

        boolean roleKnown=!hasWorkspace||owner||admin||technician||viewer;
        boolean managerBoundary=!hasWorkspace||(canSeeAllJobs()==manager&&canManageWorkspaceSettings()==manager);
        boolean fieldBoundary=!hasWorkspace||(canPerformFieldWork()==(owner||admin||technician));
        boolean viewerBoundary=!viewer||(!canPerformFieldWork()&&!canManageWorkspaceSettings()&&!canSeeAllJobs());
        boolean cloudIdentity=!cloudWorkspace||(cloudSync.signedIn()&&!accountTeam.cloudUserId().isEmpty());
        boolean technicianLink=!technician||myTechnicianId()>0;
        b.addView(section("Role boundaries"));
        b.addView(rowCard("Known workspace role",roleKnown?"Owner / Admin / Technician / Viewer or local mode":"Unexpected role value",qaResult(roleKnown)));
        b.addView(rowCard("Manager-only controls",managerBoundary?"Team, master data, backup and all-job visibility match the role":"Role and manager permissions disagree",qaResult(managerBoundary)));
        b.addView(rowCard("Field-work controls",fieldBoundary?"Create/edit/start service matches the role":"Field-work permission does not match the role",qaResult(fieldBoundary)));
        b.addView(rowCard("Viewer read-only",viewerBoundary?"No field work or workspace administration":"Viewer has a write-capable permission",qaResult(viewerBoundary)));
        b.addView(rowCard("Technician profile link",technicianLink?"Field person link is ready":"Account is not linked to an active People & Team technician",qaResult(technicianLink)));

        long pending=cloudSync.pendingChanges(),conflicts=cloudSync.conflictCount();boolean syncIdentity=cloudIdentity&&!workspaceAccessRevoked();
        b.addView(section("Multi-device sync"));b.addView(rowCard("Cloud identity",cloudWorkspace?(cloudSync.signedIn()?"Signed in and workspace bound":"Workspace bound but account session is missing"):"Local-only device",qaResult(syncIdentity||!cloudWorkspace)));b.addView(info("Pending changes",String.valueOf(pending)));b.addView(info("Protected conflicts",String.valueOf(conflicts)));b.addView(info("Last sync",cloudSync.lastSync()));b.addView(info("Last result",cloudSync.lastResult()));
        if(conflicts>0)b.addView(paragraph("Protected conflicts are expected during the conflict test. Resolve them from Cloud & Team Sync before calling the device clean."));else if(pending>0)b.addView(paragraph("This device still has local changes waiting to synchronize."));else if(cloudWorkspace)b.addView(paragraph("This device currently has a clean synchronization queue."));
        if(cloudWorkspace&&cloudSync.signedIn()&&!workspaceAccessRevoked()){MaterialButton sync=button("Sync now & recheck");sync.setOnClickListener(v->runCloud("Running QA synchronization…",()->cloudSync.syncNow(accountTeam.workspaceId(),accountTeam.canManageTeam()),obj->{CloudSyncFoundation.SyncResult r=(CloudSyncFoundation.SyncResult)obj;toast(r.message);showReleaseReadiness();}));b.addView(sync);}
        MaterialButton diagnostics=outlineButton("Open sync diagnostics");diagnostics.setOnClickListener(v->showCloudSync());b.addView(diagnostics);

        b.addView(section("Two-device test"));b.addView(paragraph("1. Sync Device A and Device B until both show zero pending changes.\n2. On Device A, edit or start an assigned job while offline; confirm it shows a locally saved/pending state.\n3. On Device B, change the same job and synchronize it.\n4. Reconnect Device A and sync. Fida Field must protect the competing local edit instead of silently overwriting it.\n5. Open Sync Diagnostics, choose the intended version, sync again, then confirm both devices show the same job and zero unresolved conflicts."));
        b.addView(section("Role test"));b.addView(paragraph("Owner/Admin: manage People & Team, master data, backup and all jobs.\nTechnician: assigned jobs and field work, but no team/master-data administration.\nViewer: read-only; no job creation, service timer, maintenance completion, backup, team or master-data changes."));
    }

'''
replace_once(MAIN,'    private void showCloudSync(){\n',qa_method+'    private void showCloudSync(){\n')

print('Fida Field 0.9.49 role & multi-device QA patch applied')
