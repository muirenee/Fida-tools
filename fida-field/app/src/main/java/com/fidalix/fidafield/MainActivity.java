package com.fidalix.fidafield;

import android.app.Activity;
import android.Manifest;
import android.app.DatePickerDialog;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;
import com.google.android.material.dialog.MaterialAlertDialogBuilder;
import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.google.android.material.materialswitch.MaterialSwitch;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.MultiFormatWriter;
import com.google.zxing.common.BitMatrix;
import com.journeyapps.barcodescanner.ScanContract;
import com.journeyapps.barcodescanner.ScanOptions;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;
import java.util.concurrent.TimeUnit;

public class MainActivity extends AppCompatActivity {
    private static final int MENU_DASH=1, MENU_JOBS=2, MENU_CUSTOMERS=3, MENU_ASSETS=4, MENU_MORE=5;
    // Runtime palette defaults to Fidalix and can be rebranded by Pro subscribers.
    private int BRAND=BrandingManager.DEFAULT_PRIMARY, BRAND_DARK=BrandingManager.DEFAULT_PRIMARY_DARK, ACCENT=BrandingManager.DEFAULT_ACCENT, ACCENT_YELLOW=BrandingManager.DEFAULT_HIGHLIGHT;
    private final int TEXT=0xFF2D312D, MUTED=0xFF70756F, BG=0xFFF5F6F4, SOFT=0xFFF0F2EF;

    private AppDatabase db;
    private SharedPreferences prefs;
    private EntitlementManager entitlements;
    private BrandingManager branding;
    private CloudSyncFoundation cloudSync;
    private AccountTeamManager accountTeam;
    private BillingManager billingManager;
    private FrameLayout content;
    private TextView title, subtitle;
    private BottomNavigationView bottom;
    private int currentMenu=MENU_DASH;
    private boolean mainTabScreen=true;

    private long photoJobId=0;
    private Uri pendingPhotoUri;

    private ActivityResultLauncher<Intent> cameraLauncher;
    private ActivityResultLauncher<String> cameraPermissionLauncher;
    private ActivityResultLauncher<String> backupLauncher;
    private ActivityResultLauncher<String[]> restoreLauncher;
    private ActivityResultLauncher<ScanOptions> qrLauncher;
    private ActivityResultLauncher<String> notificationPermissionLauncher;
    private ActivityResultLauncher<String> brandingLogoLauncher;

    static class Choice {
        long id; String label;
        Choice(long id,String label){this.id=id;this.label=label;}
        @Override public String toString(){return label;}
    }

    @Override protected void onCreate(Bundle savedInstanceState) {
        prefs=getSharedPreferences("fida_field_prefs",MODE_PRIVATE);
        applyThemeMode(prefs.getString("theme","System"));
        super.onCreate(savedInstanceState);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        db=new AppDatabase(this);
        entitlements=new EntitlementManager(prefs,db);
        branding=new BrandingManager(prefs,entitlements.isPro());
        applyBrandingPalette();
        cloudSync=new CloudSyncFoundation(this,prefs,db);
        cloudSync.deviceId();
        accountTeam=new AccountTeamManager(prefs,db);
        billingManager=new BillingManager(this,prefs,()->refreshEntitlementsAndBranding());
        billingManager.start();
        migrateDefaultTechnician();
        registerLaunchers();
        scheduleMaintenanceReminders();
        CloudSyncWorker.configure(this,prefs.getBoolean(CloudSyncWorker.KEY_ENABLED,true));
        buildChrome();
        installAppBackNavigation();
        if(captureWorkspaceInviteIntent(getIntent())||hasPendingWorkspaceInvite())showAccountWorkspace();else showDashboard();
    }

    @Override protected void onResume(){super.onResume();if(billingManager!=null)billingManager.refreshPurchases();}
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);if(captureWorkspaceInviteIntent(intent))showAccountWorkspace();}
    @Override protected void onDestroy(){if(billingManager!=null)billingManager.stop();super.onDestroy();}

    private static final String KEY_PENDING_INVITE_TOKEN="pending_workspace_invite_token";
    private static final String KEY_PENDING_INVITE_EMAIL="pending_workspace_invite_email";
    private boolean captureWorkspaceInviteIntent(Intent intent){
        Uri data=intent==null?null:intent.getData();if(data==null||!"fidafield".equalsIgnoreCase(data.getScheme())||!"workspace-invite".equalsIgnoreCase(data.getHost()))return false;
        String token=data.getQueryParameter("token"),email=data.getQueryParameter("email");if(token==null||token.trim().isEmpty())return false;
        prefs.edit().putString(KEY_PENDING_INVITE_TOKEN,token.trim()).putString(KEY_PENDING_INVITE_EMAIL,email==null?"":email.trim()).apply();return true;
    }
    private boolean hasPendingWorkspaceInvite(){return !prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim().isEmpty();}
    private String pendingWorkspaceInviteToken(){return prefs.getString(KEY_PENDING_INVITE_TOKEN,"").trim();}
    private String pendingWorkspaceInviteEmail(){return prefs.getString(KEY_PENDING_INVITE_EMAIL,"").trim();}
    private void clearPendingWorkspaceInvite(){prefs.edit().remove(KEY_PENDING_INVITE_TOKEN).remove(KEY_PENDING_INVITE_EMAIL).apply();}

    private void installAppBackNavigation(){
        getOnBackPressedDispatcher().addCallback(this,new OnBackPressedCallback(true){
            @Override public void handleOnBackPressed(){
                if(!mainTabScreen){navigate(currentMenu);return;}
                if(currentMenu!=MENU_DASH){showDashboard();return;}
                finish();
            }
        });
    }

    private void applyThemeMode(String mode){
        if("Light".equals(mode))AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);
        else if("Dark".equals(mode))AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_YES);
        else AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM);
    }

    private void applyBrandingPalette(){
        if(branding==null)return;
        BRAND=branding.primary();BRAND_DARK=branding.primaryDark();ACCENT=branding.accent();ACCENT_YELLOW=branding.highlight();
    }

    private void refreshEntitlementsAndBranding(){
        entitlements=new EntitlementManager(prefs,db);branding=new BrandingManager(prefs,entitlements.isPro());applyBrandingPalette();
    }

    private void registerLaunchers(){
        cameraPermissionLauncher=registerForActivityResult(new ActivityResultContracts.RequestPermission(), granted->{
            if(granted&&photoJobId>0){long jobId=photoJobId;launchCameraCapture(jobId);}
            else{photoJobId=0;if(!granted)showCameraPermissionRequired();}
        });
        cameraLauncher=registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result->{
            if(result.getResultCode()==Activity.RESULT_OK && photoJobId>0 && pendingPhotoUri!=null){
                db.addPhoto(photoJobId,pendingPhotoUri.toString());
                toast("Photo added");
                showJobDetail(photoJobId);
            } else if(pendingPhotoUri!=null){
                try{getContentResolver().delete(pendingPhotoUri,null,null);}catch(Exception ignored){}
            }
            pendingPhotoUri=null; photoJobId=0;
        });
        backupLauncher=registerForActivityResult(new ActivityResultContracts.CreateDocument("application/zip"), uri->{
            if(uri==null)return;
            try{exportFullBackup(uri);toast("Full backup exported");}catch(Exception e){error("Backup failed",e);}
        });
        restoreLauncher=registerForActivityResult(new ActivityResultContracts.OpenDocument(), uri->{
            if(uri==null)return;
            new MaterialAlertDialogBuilder(this).setTitle("Restore backup?").setMessage("This replaces the current local data and restores embedded photos/signatures where available.").setNegativeButton("Cancel",null).setPositiveButton("Restore",(d,w)->{
                try{restoreBackup(uri);toast("Backup restored");recreate();}catch(Exception e){error("Restore failed",e);}
            }).show();
        });
        qrLauncher=registerForActivityResult(new ScanContract(), result->{
            if(result.getContents()!=null)openScannedAsset(result.getContents());
        });
        notificationPermissionLauncher=registerForActivityResult(new ActivityResultContracts.RequestPermission(), granted->{
            toast(granted?"Maintenance notifications enabled":"Notification permission not granted");
        });
        brandingLogoLauncher=registerForActivityResult(new ActivityResultContracts.GetContent(), uri->{
            if(uri==null)return;
            if(!requireWorkspaceManager("Custom branding"))return;
            if(!entitlements.canUseCustomBranding()){showUpgradeRequired("Custom branding");return;}
            try{branding.saveLogo(this,uri);toast("Custom logo saved");showBranding();}catch(Exception e){error("Could not save logo",e);}
        });
    }

    private byte[] readAll(InputStream in)throws Exception{java.io.ByteArrayOutputStream b=new java.io.ByteArrayOutputStream();byte[] buf=new byte[8192];int n;while((n=in.read(buf))>0)b.write(buf,0,n);return b.toByteArray();}

    private void buildChrome(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(backgroundColor());
        LinearLayout bar=new LinearLayout(this);bar.setOrientation(LinearLayout.HORIZONTAL);bar.setGravity(Gravity.CENTER_VERTICAL);bar.setPadding(dp(18),dp(11),dp(18),dp(11));bar.setBackgroundColor(BRAND_DARK);
        ImageView logo=new ImageView(this);Bitmap customHeaderLogo=branding==null?null:branding.loadCustomLogo(this);if(customHeaderLogo!=null)logo.setImageBitmap(customHeaderLogo);else logo.setImageResource(R.drawable.ic_logo);logo.setAdjustViewBounds(true);logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);logo.setContentDescription(branding!=null&&branding.isActive()?"Custom company logo":"Fida Field");bar.addView(logo,new LinearLayout.LayoutParams(dp(54),dp(44)));
        LinearLayout titles=new LinearLayout(this);titles.setOrientation(LinearLayout.VERTICAL);titles.setPadding(dp(11),0,0,0);
        title=new TextView(this);title.setTextColor(onColor(BRAND_DARK));title.setTextSize(20);title.setTypeface(android.graphics.Typeface.create("sans-serif",android.graphics.Typeface.BOLD));
        subtitle=new TextView(this);subtitle.setTextColor(withAlpha(onColor(BRAND_DARK),0.78f));subtitle.setTextSize(12);subtitle.setMaxLines(1);
        titles.addView(title);titles.addView(subtitle);bar.addView(titles,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
        TextView brand=new TextView(this);brand.setText("FIELD");brand.setTextColor(ACCENT);brand.setTextSize(11);brand.setLetterSpacing(0.12f);brand.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));brand.setPadding(dp(9),dp(5),dp(9),dp(5));brand.setBackground(rounded(0xFF3A3F3A,0,0,dp(12)));bar.addView(brand);
        root.addView(bar,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT));
        View accentLine=new View(this);GradientDrawable accentGradient=new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT,new int[]{ACCENT,ACCENT_YELLOW});accentLine.setBackground(accentGradient);root.addView(accentLine,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(3)));

        content=new FrameLayout(this);root.addView(content,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1));
        bottom=new BottomNavigationView(this);bottom.setBackgroundColor(surface());bottom.setItemIconTintList(navColors());bottom.setItemTextColor(navColors());bottom.setLabelVisibilityMode(com.google.android.material.navigation.NavigationBarView.LABEL_VISIBILITY_LABELED);bottom.setItemActiveIndicatorEnabled(true);bottom.setItemActiveIndicatorColor(ColorStateList.valueOf(isNight()?0xFF3A3324:0xFFFFE8BF));bottom.setElevation(dp(8));bottom.getMenu().add(0,MENU_DASH,0,"Home").setIcon(R.drawable.ic_dashboard);bottom.getMenu().add(0,MENU_JOBS,1,"Jobs").setIcon(R.drawable.ic_jobs);bottom.getMenu().add(0,MENU_CUSTOMERS,2,"Customers").setIcon(R.drawable.ic_customers);bottom.getMenu().add(0,MENU_ASSETS,3,"Assets").setIcon(R.drawable.ic_assets);bottom.getMenu().add(0,MENU_MORE,4,"More").setIcon(R.drawable.ic_more);
        bottom.setOnItemSelectedListener(item->{navigate(item.getItemId());return true;});root.addView(bottom);
        final int barLeft=dp(18), barTop=dp(11), barRight=dp(18), barBottom=dp(11);
        ViewCompat.setOnApplyWindowInsetsListener(root,(v,insets)->{
            Insets safe=insets.getInsets(WindowInsetsCompat.Type.systemBars()|WindowInsetsCompat.Type.displayCutout());
            bar.setPadding(barLeft,barTop+safe.top,barRight,barBottom);
            bottom.setPadding(bottom.getPaddingLeft(),bottom.getPaddingTop(),bottom.getPaddingRight(),safe.bottom);
            return insets;
        });
        setContentView(root);
        ViewCompat.requestApplyInsets(root);
    }

    private ColorStateList navColors(){int[][] states={{android.R.attr.state_checked},{}};int[] colors={ACCENT,isNight()?0xFFA7ADA6:0xFF6F746E};return new ColorStateList(states,colors);}
    private boolean isNight(){return (getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK)==android.content.res.Configuration.UI_MODE_NIGHT_YES;}
    private int backgroundColor(){return isNight()?0xFF151815:BG;}
    private int surface(){return isNight()?0xFF222622:0xFFFFFFFF;}
    private int softSurface(){return isNight()?0xFF2A2F2A:SOFT;}
    private int textColor(){return isNight()?0xFFF1F3EF:TEXT;}
    private int mutedColor(){return isNight()?0xFFA9AEA8:MUTED;}
    private int borderColor(){return isNight()?0xFF3A403A:0xFFE1E4E0;}
    private int brandTextColor(){return isNight()?ACCENT:BRAND;}
    private int paleAccent(){return blend(ACCENT,isNight()?0xFF181B18:0xFFFFFFFF,isNight()?0.78f:0.88f);}
    private int paleAccentBorder(){return blend(ACCENT,isNight()?0xFF2A2E2A:0xFFFFFFFF,isNight()?0.52f:0.62f);}
    private int onColor(int color){double lum=(0.2126*Color.red(color)+0.7152*Color.green(color)+0.0722*Color.blue(color))/255.0;return lum>0.62?0xFF171917:0xFFFFFFFF;}
    private int withAlpha(int color,float alpha){return Color.argb(Math.max(0,Math.min(255,Math.round(alpha*255))),Color.red(color),Color.green(color),Color.blue(color));}
    private int blend(int a,int b,float amount){amount=Math.max(0f,Math.min(1f,amount));return Color.rgb(Math.round(Color.red(a)*(1-amount)+Color.red(b)*amount),Math.round(Color.green(a)*(1-amount)+Color.green(b)*amount),Math.round(Color.blue(a)*(1-amount)+Color.blue(b)*amount));}

    private void navigate(int id){currentMenu=id;if(workspaceAccessRevoked()&&id!=MENU_MORE){showWorkspaceAccessBlocked();return;}if(id==MENU_DASH)showDashboard();else if(id==MENU_JOBS)showJobs();else if(id==MENU_CUSTOMERS)showCustomers();else if(id==MENU_ASSETS)showAssets();else showMore();}
    private void setHeader(String a,String b){mainTabScreen=false;title.setText(a);subtitle.setText(b);}
    private void clear(){content.removeAllViews();}
    private boolean workspaceAccessRevoked(){return cloudSync!=null&&accountTeam!=null&&accountTeam.hasWorkspace()&&cloudSync.workspaceAccessRevoked(accountTeam.workspaceId());}
    private boolean canSeeAllJobs(){return !workspaceAccessRevoked()&&accountTeam!=null&&accountTeam.canManageTeam();}
    private boolean canManageWorkspaceSettings(){return !workspaceAccessRevoked()&&(accountTeam==null||!accountTeam.hasWorkspace()||accountTeam.canManageTeam());}
    private boolean canPerformFieldWork(){if(workspaceAccessRevoked())return false;if(accountTeam==null||!accountTeam.hasWorkspace())return true;String r=accountTeam.accountRole();return AccountTeamManager.ROLE_OWNER.equals(r)||AccountTeamManager.ROLE_ADMIN.equals(r)||AccountTeamManager.ROLE_TECHNICIAN.equals(r);}
    private boolean requireWorkspaceManager(String feature){if(canManageWorkspaceSettings())return true;new MaterialAlertDialogBuilder(this).setTitle("Owner or Admin only").setMessage(feature+" can only be changed by a workspace Owner or Admin. Your "+accountTeam.accountRole()+" account remains focused on assigned service work.").setPositiveButton("OK",null).show();return false;}
    private String currentJobUserUuid(){return accountTeam==null?"":accountTeam.cloudUserId();}
    private long myTechnicianId(){AppDatabase.Row t=db.technicianForUser(currentJobUserUuid());return t.id();}
    private boolean canSeeJob(AppDatabase.Row job){return job!=null&&job.id()>0&&db.jobVisibleToUser(job.id(),currentJobUserUuid(),canSeeAllJobs());}


    private ScrollView page(){ScrollView sc=new ScrollView(this);sc.setFillViewport(true);sc.setClipToPadding(false);sc.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS);LinearLayout ll=new LinearLayout(this);ll.setOrientation(LinearLayout.VERTICAL);ll.setPadding(dp(20),dp(20),dp(20),dp(40));sc.addView(ll);sc.setTag(ll);content.addView(sc,new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT));return sc;}
    private LinearLayout body(ScrollView sc){return (LinearLayout)sc.getTag();}

    private void showWorkspaceAccessBlocked(){
        currentMenu=MENU_DASH;bottom.getMenu().findItem(MENU_DASH).setChecked(true);setHeader("Workspace access","Access disabled");mainTabScreen=true;clear();LinearLayout b=body(page());
        b.addView(heroCard("Workspace access disabled","Your local copy is retained, but company workspace data and field actions are locked until your access is re-enabled and verified."));
        b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Account",cloudSync.accountEmail().isEmpty()?accountTeam.accountEmail():cloudSync.accountEmail()));b.addView(info("Last access check",cloudSync.workspaceAccessCheckedAt()));
        MaterialButton check=button("Check access again");check.setEnabled(cloudSync.backendConfigured()&&cloudSync.signedIn());check.setOnClickListener(v->runCloud("Checking workspace access…",()->cloudSync.refreshWorkspaceAccess(accountTeam.workspaceId()),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;if(wm==null){toast("Workspace access is still disabled");showWorkspaceAccessBlocked();}else{accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Workspace access restored · "+wm.role);showDashboard();}}));b.addView(check);
        MaterialButton account=outlineButton("Account & workspace");account.setOnClickListener(v->showAccountWorkspace());b.addView(account);MaterialButton sync=outlineButton("Cloud sync status");sync.setOnClickListener(v->showCloudSync());b.addView(sync);
        b.addView(paragraph("An Owner or Admin can re-enable this member from People & Team. Existing jobs and history are not deleted when access is disabled."));
    }

    private void showDashboard(){
        if(workspaceAccessRevoked()){showWorkspaceAccessBlocked();return;}
        currentMenu=MENU_DASH;bottom.getMenu().findItem(MENU_DASH).setChecked(true);setHeader("Fida Field","Service & Maintenance");mainTabScreen=true;clear();LinearLayout b=body(page());
        String tech=prefs.getString("technician_name","");b.addView(heroCard(tech.isEmpty()?"Field service, organized.":"Hello, "+tech,"Jobs, service history and customer-ready reports — even offline."));
        long openJobs=db.visibleOpenJobCount(currentJobUserUuid(),canSeeAllJobs());long due30=db.dueAssets(30).size();LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(dashboardStat("Open jobs",openJobs,v->showJobs()),new LinearLayout.LayoutParams(0,dp(102),1));stats.addView(spacerH());stats.addView(dashboardStat("Due ≤30d",due30,v->showMaintenance(30)),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats);
        MaterialCardView planCard=rowCard(entitlements.planName(),entitlements.usageSummary(),entitlements.isPro()?"PRO":entitlements.freeReportsRemaining()+" left");planCard.setOnClickListener(v->showPlan());b.addView(planCard);
        long customerCount=db.count("customers",null,null),assetCount=db.count("assets",null,null);LinearLayout stats2=new LinearLayout(this);stats2.setOrientation(LinearLayout.HORIZONTAL);stats2.setPadding(0,dp(8),0,0);stats2.addView(dashboardStat("Customers",customerCount,v->showCustomers()),new LinearLayout.LayoutParams(0,dp(102),1));stats2.addView(spacerH());stats2.addView(dashboardStat("Assets",assetCount,v->showAssets()),new LinearLayout.LayoutParams(0,dp(102),1));b.addView(stats2);
        b.addView(section("Quick actions"));LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);if(canPerformFieldWork()){MaterialButton newJob=button("+ New job");newJob.setOnClickListener(v->showJobDialog(0,0));actions.addView(newJob,new LinearLayout.LayoutParams(0,dp(52),1));}if(canManageWorkspaceSettings()){if(actions.getChildCount()>0)actions.addView(spacerH());MaterialButton newClient=outlineButton("+ Customer");newClient.setOnClickListener(v->showCustomerDialog(0));actions.addView(newClient,new LinearLayout.LayoutParams(0,dp(52),1));}if(actions.getChildCount()>0)b.addView(actions);else b.addView(paragraph("Viewer access is read-only."));
        List<AppDatabase.Row> due=db.dueAssets(30);b.addView(section("Maintenance attention"));if(due.isEmpty())b.addView(empty("Nothing due in the next 30 days."));else for(int i=0;i<Math.min(4,due.size());i++){AppDatabase.Row r=due.get(i);MaterialCardView c=rowCard(r.s("name"),r.s("customer_name")+" • Due "+r.s("next_service"),r.s("tag"));c.setOnClickListener(v->showAssetDetail(r.id()));b.addView(c);}
        List<AppDatabase.Row> recent=db.recentJobsScoped(4,currentJobUserUuid(),canSeeAllJobs());b.addView(section("Recent jobs"));if(recent.isEmpty())b.addView(empty("Create your first service job to start a history."));else for(AppDatabase.Row r:recent){MaterialCardView c=rowCard(r.s("report_no")+" · "+r.s("title"),r.s("customer_name")+" • "+r.s("job_date"),r.s("status"));c.setOnClickListener(v->showJobDetail(r.id()));b.addView(c);}
    }

    private void showJobs(){
        currentMenu=MENU_JOBS;bottom.getMenu().findItem(MENU_JOBS).setChecked(true);setHeader("Jobs","Search, filter & service history");mainTabScreen=true;clear();LinearLayout b=body(page());
        if(canPerformFieldWork()){MaterialButton add=button("+ New service job");add.setOnClickListener(v->showJobDialog(0,0));b.addView(add,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(52)));}else b.addView(paragraph("Viewer access is read-only. You can review jobs available to your account."));
        EditText search=input("Search report, customer, site, asset, technician…","");b.addView(search);
        b.addView(label("Status"));Spinner status=spinner(new String[]{"All","Open","In Progress","Completed","Cancelled"});b.addView(status);
        LinearLayout filters=new LinearLayout(this);filters.setOrientation(LinearLayout.HORIZONTAL);Spinner priority=spinner(new String[]{"All","Low","Normal","High","Urgent"});Spinner date=spinner(new String[]{"All dates","Today","Last 7 days","Last 30 days","This year"});filters.addView(priority,new LinearLayout.LayoutParams(0,dp(52),1));filters.addView(spacerH());filters.addView(date,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(label("Priority / date"));b.addView(filters);
        b.addView(label("Technician"));Spinner technician=spinner(canSeeAllJobs()?technicianFilterValues():new String[]{"My assigned jobs"});b.addView(technician);
        LinearLayout list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);b.addView(list);
        Runnable reload=()->{String[] range=dateRange(String.valueOf(date.getSelectedItem()));renderJobs(list,search.getText().toString(),String.valueOf(status.getSelectedItem()),String.valueOf(priority.getSelectedItem()),String.valueOf(technician.getSelectedItem()),range[0],range[1]);};
        search.addTextChangedListener(watcher(reload));AdapterView.OnItemSelectedListener l=new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long id){reload.run();}public void onNothingSelected(AdapterView<?>p){}};status.setOnItemSelectedListener(l);priority.setOnItemSelectedListener(l);date.setOnItemSelectedListener(l);technician.setOnItemSelectedListener(l);reload.run();
    }
    private void renderJobs(LinearLayout list,String q,String status,String priority,String technician,String from,String to){list.removeAllViews();String techFilter=canSeeAllJobs()?technician:"All";List<AppDatabase.Row> rows=db.jobsFilteredScoped(q,status,priority,techFilter,from,to,currentJobUserUuid(),canSeeAllJobs());if(rows.isEmpty()){list.addView(empty("No matching jobs."));return;}TextView count=paragraph(rows.size()+" job(s) found");list.addView(count);for(AppDatabase.Row r:rows){String who=r.s("customer_name").isEmpty()?"No customer":r.s("customer_name");String meta=who+(r.s("site_name").isEmpty()?"":" • "+r.s("site_name"))+" • "+r.s("job_date")+(r.s("technician").isEmpty()?"":" • "+r.s("technician"));String badge=r.s("status")+("Normal".equals(r.s("priority"))||r.s("priority").isEmpty()?"":" · "+r.s("priority"));MaterialCardView c=rowCard(r.s("report_no")+" · "+r.s("title"),meta,badge);c.setOnClickListener(v->showJobDetail(r.id()));list.addView(c);}}

    private void showCustomers(){
        currentMenu=MENU_CUSTOMERS;bottom.getMenu().findItem(MENU_CUSTOMERS).setChecked(true);setHeader("Customers","Customers, sites & service history");mainTabScreen=true;clear();LinearLayout b=body(page());
        if(canManageWorkspaceSettings()){LinearLayout a=new LinearLayout(this);a.setOrientation(LinearLayout.HORIZONTAL);MaterialButton cbtn=button("+ Customer");cbtn.setOnClickListener(v->showCustomerDialog(0));a.addView(cbtn,new LinearLayout.LayoutParams(0,dp(52),1));a.addView(spacerH());MaterialButton sbtn=outlineButton("+ Site");sbtn.setOnClickListener(v->showSiteDialog(0,0));a.addView(sbtn,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(a);}else b.addView(paragraph("Customer and site master data is read-only for "+accountTeam.accountRole()+" accounts."));
        EditText search=input("Search customer, site, contact…","");b.addView(search);LinearLayout list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);b.addView(list);
        Runnable reload=()->{list.removeAllViews();String q=search.getText().toString().trim().toLowerCase(Locale.US);list.addView(section("Customers"));int customerCount=0;for(AppDatabase.Row r:db.customers()){String hay=(r.s("name")+" "+r.s("contact")+" "+r.s("phone")+" "+r.s("email")).toLowerCase(Locale.US);if(!q.isEmpty()&&!hay.contains(q))continue;customerCount++;long sites=db.count("sites","customer_id=?",new String[]{String.valueOf(r.id())});long jobs=db.jobsForCustomerScoped(r.id(),currentJobUserUuid(),canSeeAllJobs()).size();MaterialCardView card=rowCard(r.s("name"),(r.s("contact").isEmpty()?"No contact":r.s("contact"))+" • "+sites+" site(s) • "+jobs+" job(s)",r.s("phone"));card.setOnClickListener(v->showCustomerDetail(r.id()));list.addView(card);}if(customerCount==0)list.addView(empty("No matching customers."));list.addView(section("Sites"));int siteCount=0;for(AppDatabase.Row r:db.sites(0)){String hay=(r.s("name")+" "+r.s("customer_name")+" "+r.s("address")+" "+r.s("contact")+" "+r.s("phone")).toLowerCase(Locale.US);if(!q.isEmpty()&&!hay.contains(q))continue;siteCount++;MaterialCardView card=rowCard(r.s("name"),r.s("customer_name"),r.s("address"));card.setOnClickListener(v->showSiteDetail(r.id()));list.addView(card);}if(siteCount==0)list.addView(empty("No matching sites."));};search.addTextChangedListener(watcher(reload));reload.run();
    }

    private void showCustomerDetail(long id){
        AppDatabase.Row c=db.getCustomer(id);if(c.id()==0){toast("Customer not found");return;}setHeader(c.s("name"),"Customer service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showCustomerDialog(id));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);
        b.addView(section("Customer profile"));b.addView(info("Contact",c.s("contact")));b.addView(info("Phone",c.s("phone")));b.addView(info("Email",c.s("email")));b.addView(info("Address",c.s("address")));addIf(b,"Notes",c.s("notes"));
        LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(stat("Sites",db.count("sites","customer_id=?",new String[]{String.valueOf(id)})),new LinearLayout.LayoutParams(0,dp(100),1));stats.addView(spacerH());stats.addView(stat("Assets",db.count("assets","customer_id=?",new String[]{String.valueOf(id)})),new LinearLayout.LayoutParams(0,dp(100),1));stats.addView(spacerH());stats.addView(stat("Jobs",db.jobsForCustomerScoped(id,currentJobUserUuid(),canSeeAllJobs()).size()),new LinearLayout.LayoutParams(0,dp(100),1));b.addView(stats);
        if(canManageWorkspaceSettings()){MaterialButton addSite=button("+ Add service site");addSite.setOnClickListener(v->showSiteDialog(0,id));b.addView(addSite);}
        List<AppDatabase.Row> sites=db.sites(id);b.addView(section("Sites ("+sites.size()+")"));if(sites.isEmpty())b.addView(empty("No sites for this customer."));for(AppDatabase.Row r:sites){MaterialCardView card=rowCard(r.s("name"),r.s("address"),r.s("phone"));card.setOnClickListener(v->showSiteDetail(r.id()));b.addView(card);}
        List<AppDatabase.Row> assets=db.assets(id,0);b.addView(section("Assets ("+assets.size()+")"));if(assets.isEmpty())b.addView(empty("No assets assigned to this customer."));for(AppDatabase.Row r:assets){MaterialCardView card=rowCard(r.s("tag")+" · "+r.s("name"),r.s("site_name"),r.s("next_service").isEmpty()?"":"Due "+r.s("next_service"));card.setOnClickListener(v->showAssetDetail(r.id()));b.addView(card);}
        List<AppDatabase.Row> jobs=db.jobsForCustomerScoped(id,currentJobUserUuid(),canSeeAllJobs());b.addView(section("Service jobs ("+jobs.size()+")"));if(jobs.isEmpty())b.addView(empty("No jobs recorded for this customer."));for(AppDatabase.Row r:jobs){MaterialCardView card=rowCard(r.s("report_no")+" · "+r.s("title"),r.s("job_date")+(r.s("site_name").isEmpty()?"":" • "+r.s("site_name")),r.s("status"));card.setOnClickListener(v->showJobDetail(r.id()));b.addView(card);}
    }

    private void showSiteDetail(long id){
        AppDatabase.Row s=db.getSite(id);if(s.id()==0){toast("Site not found");return;}AppDatabase.Row c=db.getCustomer(parse(s.s("customer_id")));setHeader(s.s("name"),"Site service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Customers");back.setOnClickListener(v->showCustomers());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showSiteDialog(id,parse(s.s("customer_id"))));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);
        b.addView(section("Site profile"));b.addView(info("Customer",c.s("name")));b.addView(info("Address",s.s("address")));b.addView(info("Contact",s.s("contact")));b.addView(info("Phone",s.s("phone")));addIf(b,"Notes",s.s("notes"));
        List<AppDatabase.Row> assets=db.assets(0,id);List<AppDatabase.Row> jobs=db.jobsForSiteScoped(id,currentJobUserUuid(),canSeeAllJobs());LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(stat("Assets",assets.size()),new LinearLayout.LayoutParams(0,dp(100),1));stats.addView(spacerH());stats.addView(stat("Jobs",jobs.size()),new LinearLayout.LayoutParams(0,dp(100),1));b.addView(stats);
        b.addView(section("Assets ("+assets.size()+")"));if(assets.isEmpty())b.addView(empty("No assets at this site."));for(AppDatabase.Row r:assets){MaterialCardView card=rowCard(r.s("tag")+" · "+r.s("name"),r.s("location"),r.s("next_service").isEmpty()?"":"Due "+r.s("next_service"));card.setOnClickListener(v->showAssetDetail(r.id()));b.addView(card);}
        b.addView(section("Service jobs ("+jobs.size()+")"));if(jobs.isEmpty())b.addView(empty("No jobs recorded at this site."));for(AppDatabase.Row r:jobs){MaterialCardView card=rowCard(r.s("report_no")+" · "+r.s("title"),r.s("job_date")+(r.s("asset_name").isEmpty()?"":" • "+r.s("asset_name")),r.s("status"));card.setOnClickListener(v->showJobDetail(r.id()));b.addView(card);}
    }

    private void showAssets(){
        currentMenu=MENU_ASSETS;bottom.getMenu().findItem(MENU_ASSETS).setChecked(true);setHeader("Assets","Equipment & maintenance");mainTabScreen=true;clear();LinearLayout b=body(page());
        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);if(canManageWorkspaceSettings()){MaterialButton add=button("+ Add asset");add.setOnClickListener(v->showAssetDialog(0));actions.addView(add,new LinearLayout.LayoutParams(0,dp(52),1));actions.addView(spacerH());}MaterialButton scan=outlineButton("Scan QR");scan.setOnClickListener(v->scanAssetQr());actions.addView(scan,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(actions);
        EditText search=input("Search asset, tag, serial…","");b.addView(search);LinearLayout list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);b.addView(list);Runnable reload=()->{list.removeAllViews();String q=search.getText().toString().trim().toLowerCase(Locale.US);for(AppDatabase.Row r:db.assets(0,0)){String hay=(r.s("name")+" "+r.s("tag")+" "+r.s("serial")+" "+r.s("customer_name")).toLowerCase(Locale.US);if(!q.isEmpty()&&!hay.contains(q))continue;String meta=r.s("customer_name")+(r.s("site_name").isEmpty()?"":" • "+r.s("site_name"));String badge=r.s("next_service").isEmpty()?r.s("tag"):"Due "+r.s("next_service");MaterialCardView card=rowCard(r.s("name"),meta,badge);card.setOnClickListener(v->showAssetDetail(r.id()));list.addView(card);}if(list.getChildCount()==0)list.addView(empty("No matching assets."));};search.addTextChangedListener(watcher(reload));reload.run();
    }

    private void showMore(){
        currentMenu=MENU_MORE;bottom.getMenu().findItem(MENU_MORE).setChecked(true);setHeader("More","Reports, maintenance & settings");mainTabScreen=true;clear();LinearLayout b=body(page());
        b.addView(brandPanel());
        b.addView(section("Workspace"));
        b.addView(menuCard("PDF reports","Generate and share completed service reports",v->showReports()));
        b.addView(menuCard("Maintenance planner","Assets due, overdue and recurring service",v->showMaintenance()));
        if(canManageWorkspaceSettings()){
            b.addView(menuCard("People & Team",db.technicians().size()+" field technicians • "+accountTeam.teamSummary(),v->showPeopleTeam()));
            b.addView(menuCard("Backup & restore","Export or restore all local business data",v->showBackup()));
        }
        b.addView(menuCard("Plan & subscription",entitlements.planName()+" • "+entitlements.usageSummary(),v->showPlan()));
        if(canManageWorkspaceSettings())b.addView(menuCard("Custom branding · Pro",entitlements.isPro()?(branding.isActive()?"Active custom company identity":"Logo, colors and branded PDFs"):"Subscriber feature · upgrade to unlock",v->{if(entitlements.canUseCustomBranding())showBranding();else showUpgradeRequired("Custom branding");}));
        b.addView(menuCard("Account & workspace",accountTeam.hasWorkspace()?accountTeam.workspaceName()+" • "+accountTeam.accountRole():"Set up account and workspace",v->showAccountWorkspace()));
        b.addView(menuCard("Cloud & team sync",cloudSync.backendStatus()+" • "+cloudSync.pendingChanges()+" pending",v->showCloudSync()));
        if(canManageWorkspaceSettings())b.addView(menuCard("Company settings","Company identity, report numbering and application preferences",v->showSettings()));
        else b.addView(paragraph(accountTeam.accountRole()+" access: work with assigned service jobs and operational data. Company settings, team administration, branding, backups and master-data changes are restricted to Owner/Admin."));
        b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.23 Test\nPeople access enable/disable controls, refined home dashboard and professional service reporting by Fidalix."));
    }

    private void showReports(){
        setHeader("Reports","PDF reports & data exports");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        if(canManageWorkspaceSettings()){b.addView(section("Data exports"));LinearLayout exports=new LinearLayout(this);exports.setOrientation(LinearLayout.HORIZONTAL);MaterialButton jobsCsv=outlineButton("Jobs CSV · Pro");jobsCsv.setOnClickListener(v->{if(entitlements.canExportCsv())shareCsv("jobs");else showUpgradeRequired("CSV export");});exports.addView(jobsCsv,new LinearLayout.LayoutParams(0,dp(50),1));exports.addView(spacerH());MaterialButton assetsCsv=outlineButton("Assets CSV · Pro");assetsCsv.setOnClickListener(v->{if(entitlements.canExportCsv())shareCsv("assets");else showUpgradeRequired("CSV export");});exports.addView(assetsCsv,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(exports);b.addView(paragraph("Workspace data exports are restricted to Owner/Admin."));}
        List<AppDatabase.Row> rows=db.jobsFilteredScoped("","Completed","All","All","","",currentJobUserUuid(),canSeeAllJobs());b.addView(section("Completed jobs"));if(rows.isEmpty())b.addView(empty("Complete a job before generating its final report."));for(AppDatabase.Row r:rows){MaterialCardView card=rowCard(r.s("report_no")+" · "+r.s("title"),r.s("customer_name")+" • "+r.s("job_date"),"PDF");card.setOnClickListener(v->generateAndShare(r.id()));b.addView(card);}
    }

    private void showMaintenance(){showMaintenance(90);}
    private void showMaintenance(int days){
        int window=Math.max(1,days);setHeader("Maintenance","Upcoming & overdue service");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->navigate(currentMenu));b.addView(back);List<AppDatabase.Row> rows=db.dueAssets(window);b.addView(section("Due within "+window+" days"));if(rows.isEmpty())b.addView(empty("No maintenance due in the next "+window+" days."));else for(AppDatabase.Row r:rows){String state=r.s("next_service").compareTo(db.today())<0?"OVERDUE":"Due "+r.s("next_service");MaterialCardView card=rowCard(r.s("name"),r.s("customer_name")+(r.s("site_name").isEmpty()?"":" • "+r.s("site_name")),state);card.setOnClickListener(v->showMaintenanceAction(r));b.addView(card);}
    }

    private void showMaintenanceAction(AppDatabase.Row asset){
        if(canSeeAllJobs()){String[] actions={"Create service job","Mark serviced now","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else if(which==1)showQuickMaintenanceDialog(asset);else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}else{String[] actions={"Create my service job","View asset history"};new MaterialAlertDialogBuilder(this).setTitle(asset.s("name")+" · "+asset.s("tag")).setMessage("Next service: "+asset.s("next_service")).setItems(actions,(d,which)->{if(which==0)showJobDialog(0,asset.id());else showAssetDetail(asset.id());}).setNegativeButton("Close",null).show();}
    }

    private void showQuickMaintenanceDialog(AppDatabase.Row asset){
        LinearLayout f=form();EditText notes=multi("Service notes","Preventive maintenance completed");EditText next=input("Next service date",db.suggestNextService(asset.id(),db.today()));next.setFocusable(false);next.setOnClickListener(v->pickDate(next));f.addView(notes);f.addView(next);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Mark serviced · "+asset.s("tag")).setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{db.completeMaintenance(asset.id(),0,val(notes),val(next));d.dismiss();toast(val(next).isEmpty()?"Maintenance recorded":"Maintenance recorded • next "+val(next));showMaintenance();}));d.show();
    }

    private void showBackup(){
        if(!requireWorkspaceManager("Backup & restore"))return;
        setHeader("Backup & Restore","Keep a portable copy of local data");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);b.addView(section("Full local backup"));b.addView(paragraph("Creates one portable ZIP containing customers, sites, assets, jobs, maintenance history, company settings, job photos, customer signatures and custom branding assets when present."));MaterialButton exp=button("Export full ZIP backup");exp.setOnClickListener(v->backupLauncher.launch("FidaField-full-backup-"+db.today()+".zip"));b.addView(exp);MaterialButton imp=outlineButton("Restore backup");imp.setOnClickListener(v->restoreLauncher.launch(new String[]{"application/zip","application/json","text/plain"}));b.addView(imp);
    }

    private void showPlan(){
        setHeader("Plan & Subscription",BuildConfig.OPEN_EDITION?"Fidalix internal edition":"Company workspace subscription");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        refreshEntitlementsAndBranding();
        b.addView(section("Current plan"));b.addView(info("Plan",entitlements.planName()));b.addView(info("Entitlement",entitlements.entitlementSource()));b.addView(info("Subscription scope",BuildConfig.OPEN_EDITION?"Internal Fidalix build":"Company / workspace"));b.addView(info("Monthly usage",entitlements.usageSummary()));
        if(cloudSync!=null&&accountTeam!=null&&cloudSync.signedIn()&&accountTeam.hasCloudWorkspace()&&accountTeam.canManageTeam()){
            b.addView(section("AI report assistant"));TextView aiState=paragraph("Loading workspace AI allowance…");b.addView(aiState);MaterialButton aiRefresh=outlineButton("Refresh AI usage");aiRefresh.setOnClickListener(v->refreshAiUsage(aiState));b.addView(aiRefresh);refreshAiUsage(aiState);
        }else if(entitlements.canUseAiReportAssistant()){
            b.addView(section("AI report assistant"));b.addView(paragraph("AI report writing is available with this plan. Owner/Admin can view the workspace allowance after signing in to the cloud workspace."));
        }
        if(BuildConfig.OPEN_EDITION){
            b.addView(section("Fidalix Open"));b.addView(paragraph("This internal company edition does not use Google Play Billing. Pro capabilities are permanently enabled by the signed build itself, while cloud accounts, workspace security and Supabase synchronization continue to work normally. Keep this APK for authorized internal distribution."));b.addView(info("Billing","Not required"));b.addView(info("Distribution","Direct/internal APK"));return;
        }
        b.addView(info("Free allowance",EntitlementManager.FREE_MONTHLY_REPORT_LIMIT+" new service reports / month"));
        b.addView(section("Google Play Pro · workspace plan"));b.addView(paragraph("One verified subscription upgrades the company workspace, not one phone. The Owner or an Admin purchases through Google Play; every active member of that workspace inherits the Pro plan on their own Android device after signing in and refreshing the workspace entitlement."));
        b.addView(info("Billing status",billingManager==null?"Initializing":billingManager.lastResult()));b.addView(info("Subscription state",billingManager==null||billingManager.subscriptionState().isEmpty()?"Not verified":billingManager.subscriptionState()));b.addView(info("Expires",billingManager==null||billingManager.expiry().isEmpty()?"—":billingManager.expiry()));
        boolean readyAccount=cloudSync.signedIn()&&accountTeam.hasCloudWorkspace();boolean manager=readyAccount&&accountTeam.canManageTeam();
        if(!readyAccount){b.addView(paragraph("Sign in and create or join a cloud workspace first. Subscriptions are attached to the company workspace rather than to this device."));MaterialButton account=outlineButton("Open Account & Workspace");account.setOnClickListener(v->showAccountWorkspace());b.addView(account);}else if(!manager){b.addView(paragraph("Your workspace role is "+accountTeam.accountRole()+". You inherit the company plan automatically; only an Owner or Admin needs to purchase or manage billing."));}
        String monthly=billingManager==null?"Not loaded":billingManager.displayPrice(EntitlementManager.PRODUCT_PRO_MONTHLY);String annual=billingManager==null?"Not loaded":billingManager.displayPrice(EntitlementManager.PRODUCT_PRO_ANNUAL);
        if(manager){MaterialButton buyMonthly=button("Monthly workspace Pro · "+monthly);buyMonthly.setOnClickListener(v->{if(billingManager!=null)billingManager.purchase(this,EntitlementManager.PRODUCT_PRO_MONTHLY);});b.addView(buyMonthly);MaterialButton buyAnnual=button("Annual workspace Pro · "+annual);buyAnnual.setOnClickListener(v->{if(billingManager!=null)billingManager.purchase(this,EntitlementManager.PRODUCT_PRO_ANNUAL);});b.addView(buyAnnual);MaterialButton restore=outlineButton("Restore purchaser's Google Play subscription");restore.setOnClickListener(v->{if(billingManager!=null){billingManager.restore();toast("Checking Google Play purchase…");}});b.addView(restore);}
        MaterialButton refresh=outlineButton("Refresh workspace plan");refresh.setEnabled(readyAccount);refresh.setOnClickListener(v->{if(billingManager!=null){billingManager.refreshServerEntitlement();toast("Refreshing workspace entitlement…");}});b.addView(refresh);
        b.addView(paragraph("Field-only people who do not sign in do not consume a separate app subscription. Workspace members can install Fida Field on their own devices and use the same company plan according to their access role."));
    }

    private void refreshAiUsage(TextView host){
        if(host==null||cloudSync==null||accountTeam==null||!cloudSync.signedIn()||!accountTeam.hasCloudWorkspace()){if(host!=null)host.setText("Cloud workspace sign-in required.");return;}
        host.setText("Refreshing workspace AI usage…");
        new Thread(()->{try{JSONObject u=cloudSync.aiUsage(accountTeam.workspaceId());int used=u.optInt("used_this_month",0),limit=u.optInt("monthly_limit",0),remaining=u.optInt("remaining",0);boolean enabled=u.optBoolean("enabled",false),entitled=u.optBoolean("entitled",false);String period=u.optString("period_start","")+" → "+u.optString("period_end","");String msg=(enabled?"Service enabled":"Service paused")+" · "+(entitled?"Workspace entitled":"No active AI entitlement")+"\nThis month: "+used+" / "+limit+" assists · "+remaining+" remaining"+(period.trim().equals("→")?"":"\nPeriod: "+period);runOnUiThread(()->host.setText(msg));}catch(Exception e){String msg=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();runOnUiThread(()->host.setText("AI usage unavailable: "+msg));}}).start();
    }

    private void showBranding(){
        if(!requireWorkspaceManager("Custom branding"))return;
        if(!entitlements.canUseCustomBranding()){showUpgradeRequired("Custom branding");return;}
        setHeader("Custom Branding","Pro workspace & PDF identity");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        b.addView(section("Subscriber branding"));b.addView(paragraph("Use your own company logo and colors throughout the Fida Field workspace and generated service-report PDFs. Your settings are retained if Pro expires, but Fidalix defaults are shown until the subscription is active again."));
        MaterialSwitch enabled=new MaterialSwitch(this);enabled.setText("Enable custom branding");enabled.setChecked(prefs.getBoolean(BrandingManager.KEY_ENABLED,false));b.addView(enabled);
        b.addView(section("Company logo"));b.addView(brandingPreviewLogo());LinearLayout logoActions=new LinearLayout(this);logoActions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton choose=button(branding.hasCustomLogo(this)?"Replace logo":"Choose logo");choose.setOnClickListener(v->brandingLogoLauncher.launch("image/*"));logoActions.addView(choose,new LinearLayout.LayoutParams(0,dp(50),1));logoActions.addView(spacerH());MaterialButton remove=outlineButton("Remove logo");remove.setEnabled(branding.hasCustomLogo(this));remove.setOnClickListener(v->{branding.removeLogo(this);toast("Custom logo removed");showBranding();});logoActions.addView(remove,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(logoActions);
        EditText primary=input("Primary color · #RRGGBB",branding.primaryHex());EditText accent=input("Accent color · #RRGGBB",branding.accentHex());EditText highlight=input("Highlight color · #RRGGBB",branding.highlightHex());b.addView(section("Brand colors"));b.addView(primary);b.addView(accent);b.addView(highlight);
        LinearLayout preview=new LinearLayout(this);preview.setOrientation(LinearLayout.VERTICAL);b.addView(section("Preview"));b.addView(preview);Runnable render=()->renderBrandPreview(preview,val(primary),val(accent),val(highlight));primary.addTextChangedListener(watcher(render));accent.addTextChangedListener(watcher(render));highlight.addTextChangedListener(watcher(render));render.run();
        MaterialButton save=button("Save & apply branding");save.setOnClickListener(v->{if(!BrandingManager.isValidHex(val(primary))){primary.setError("Use #RRGGBB");return;}if(!BrandingManager.isValidHex(val(accent))){accent.setError("Use #RRGGBB");return;}if(!BrandingManager.isValidHex(val(highlight))){highlight.setError("Use #RRGGBB");return;}enabled.setChecked(true);branding.save(true,val(primary),val(accent),val(highlight));refreshEntitlementsAndBranding();toast("Custom branding applied");recreate();});b.addView(save);
        MaterialButton reset=outlineButton("Reset to Fidalix defaults");reset.setOnClickListener(v->new MaterialAlertDialogBuilder(this).setTitle("Reset branding?").setMessage("This removes the custom logo and color settings. Fida Field will return to the Fidalix palette.").setNegativeButton("Cancel",null).setPositiveButton("Reset",(d,w)->{branding.reset(this);refreshEntitlementsAndBranding();toast("Fidalix branding restored");recreate();}).show());b.addView(reset);
        b.addView(paragraph("Note: custom branding changes the workspace and PDF identity. The Android launcher/Play Store app identity remains Fida Field so updates and store integrity are preserved."));
    }

    private View brandingPreviewLogo(){
        MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(16));c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));c.setCardElevation(0);ImageView iv=new ImageView(this);Bitmap bm=branding.loadCustomLogo(this);if(bm!=null)iv.setImageBitmap(bm);else iv.setImageResource(R.drawable.fidalix_logo);iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE);iv.setAdjustViewBounds(true);iv.setPadding(dp(14),dp(10),dp(14),dp(10));c.addView(iv,new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(90)));return c;
    }

    private void renderBrandPreview(LinearLayout host,String p,String a,String h){
        host.removeAllViews();int primary=BrandingManager.parseColor(p,BRAND),accent=BrandingManager.parseColor(a,ACCENT),highlight=BrandingManager.parseColor(h,ACCENT_YELLOW);MaterialCardView card=new MaterialCardView(this);card.setRadius(dp(18));card.setCardBackgroundColor(primary);card.setCardElevation(0);LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(dp(16),dp(14),dp(16),dp(14));TextView name=new TextView(this);name.setText(prefs.getString("company_name","Your company"));name.setTextSize(18);name.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);name.setTextColor(onColor(primary));TextView copy=new TextView(this);copy.setText("Service & Maintenance · branded report preview");copy.setTextSize(12);copy.setTextColor(withAlpha(onColor(primary),0.78f));box.addView(name);box.addView(copy);LinearLayout bars=new LinearLayout(this);bars.setOrientation(LinearLayout.HORIZONTAL);bars.setPadding(0,dp(12),0,0);View x=new View(this);x.setBackgroundColor(accent);bars.addView(x,new LinearLayout.LayoutParams(0,dp(7),2));View y=new View(this);y.setBackgroundColor(highlight);bars.addView(y,new LinearLayout.LayoutParams(0,dp(7),1));box.addView(bars);card.addView(box);host.addView(card,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT));
    }

    private interface CloudWork { Object run() throws Exception; }
    private void runCloud(String started,CloudWork work,java.util.function.Consumer<Object> success){
        toast(started);new Thread(()->{try{Object result=work.run();runOnUiThread(()->success.accept(result));}catch(Exception e){String msg=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();cloudSync.markSyncResult(false,db.now(),msg);runOnUiThread(()->new MaterialAlertDialogBuilder(this).setTitle("Cloud operation failed").setMessage(msg).setPositiveButton("OK",null).show());}}).start();
    }

    private void showPendingInviteOnboarding(LinearLayout b){
        String token=pendingWorkspaceInviteToken(),invitedEmail=pendingWorkspaceInviteEmail();
        b.addView(section("Workspace invitation"));b.addView(paragraph("Invitation loaded from your email. New users only enter their name and choose a password; Fida Field creates the account, verifies the invitation and joins the workspace in one step. Existing users can sign in and join."));
        if(!cloudSync.backendConfigured()){b.addView(empty("This build does not contain the Supabase cloud configuration."));return;}
        if(cloudSync.signedIn()){
            String signed=cloudSync.accountEmail();b.addView(info("Signed in as",signed));
            if(!invitedEmail.isEmpty()&&!signed.equalsIgnoreCase(invitedEmail)){b.addView(empty("This invitation is for "+invitedEmail+", but this device is signed in as "+signed+"."));MaterialButton out=outlineButton("Sign out and use invited email");out.setOnClickListener(v->runCloud("Signing out…",()->{cloudSync.signOut();return null;},obj->{accountTeam.clearCloudBinding();showAccountWorkspace();}));b.addView(out);return;}
            MaterialButton join=button("Join workspace now");join.setOnClickListener(v->acceptPendingInviteNow(accountTeam.accountName()));b.addView(join);return;
        }
        EditText name=input("Your name",accountTeam.accountName().isEmpty()?prefs.getString("technician_name",""):accountTeam.accountName());EditText email=input("Invited email",invitedEmail);if(!invitedEmail.isEmpty())email.setEnabled(false);EditText password=input("Password","");password.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(name);b.addView(email);b.addView(password);
        MaterialButton create=button("Create account & join");create.setOnClickListener(v->{String n=val(name),e=val(email),pw=val(password);if(n.isEmpty()){name.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(pw.length()<8){password.setError("Use at least 8 characters");return;}runCloud("Creating your account and joining workspace…",()->cloudSync.registerInvitedUser(token,n,pw),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudAccount(cloudSync.userId(),n,cloudSync.accountEmail());accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);clearPendingWorkspaceInvite();runCloud("Loading your workspace…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Welcome to "+wm.name+" · "+wm.role);showDashboard();});});});b.addView(create);
        MaterialButton signIn=outlineButton("Already registered? Sign in & join");signIn.setOnClickListener(v->{String n=val(name),e=val(email),pw=val(password);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(pw.isEmpty()){password.setError("Password required");return;}runCloud("Signing in…",()->cloudSync.signIn(e,pw),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);acceptPendingInviteNow(n);});});b.addView(signIn);
        b.addView(paragraph("Fallback: if the email button did not open Fida Field, you can still sign in normally and use the invitation code shown in the email."));
    }

    private void acceptPendingInviteNow(String displayName){
        String token=pendingWorkspaceInviteToken();if(token.isEmpty()){showAccountWorkspace();return;}
        runCloud("Joining workspace…",()->cloudSync.acceptInvite(token),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudAccount(cloudSync.userId(),displayName,cloudSync.accountEmail());accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);clearPendingWorkspaceInvite();runCloud("Loading your workspace…",()->cloudSync.syncNow(wm.id,accountTeam.canManageTeam()),sync->{toast("Joined "+wm.name+" as "+wm.role);showDashboard();});});
    }

    private void showAccountWorkspace(){
        setHeader("Account & Workspace","Identity, workspace access & cloud sync");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        if(hasPendingWorkspaceInvite()&&!accountTeam.hasCloudWorkspace()){showPendingInviteOnboarding(b);return;}
        EditText workspace=input("Workspace / company name",accountTeam.workspaceName().isEmpty()?prefs.getString("company_name","Fidalix Limited"):accountTeam.workspaceName());EditText person=input("Your name",accountTeam.accountName().isEmpty()?prefs.getString("technician_name",""):accountTeam.accountName());EditText localEmail=input("Account email",accountTeam.accountEmail().isEmpty()?prefs.getString("company_email",""):accountTeam.accountEmail());
        if(canManageWorkspaceSettings()){b.addView(section("Local workspace"));b.addView(workspace);b.addView(person);b.addView(localEmail);MaterialButton save=outlineButton(accountTeam.hasWorkspace()?"Save local profile":"Create local workspace");save.setOnClickListener(v->{if(val(workspace).isEmpty()){workspace.setError("Workspace name required");return;}if(val(person).isEmpty()){person.setError("Your name required");return;}if(!val(localEmail).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(localEmail)).matches()){localEmail.setError("Enter a valid email");return;}accountTeam.saveOwnerWorkspace(val(workspace),val(person),val(localEmail));toast("Local workspace profile saved");showAccountWorkspace();});b.addView(save);}else{b.addView(section("Your workspace access"));b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Name",accountTeam.accountName()));b.addView(info("Email",accountTeam.accountEmail()));b.addView(info("Role",accountTeam.accountRole()));b.addView(paragraph("Workspace/company identity is controlled by Owner/Admin. Your account can still sync and work with the service jobs allowed by your role."));}
        b.addView(section("Cloud account"));b.addView(info("Provider",cloudSync.providerName()));b.addView(info("Backend",cloudSync.backendStatus()));
        if(!cloudSync.backendConfigured()){b.addView(empty("This build does not contain the Supabase publishable configuration."));return;}
        if(!cloudSync.signedIn()){
            EditText cloudEmail=input("Email",val(localEmail));EditText password=input("Password","");password.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);b.addView(cloudEmail);b.addView(password);
            LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton signIn=button("Sign in");MaterialButton signUp=outlineButton("Create account");actions.addView(signIn,new LinearLayout.LayoutParams(0,dp(52),1));actions.addView(spacerH());actions.addView(signUp,new LinearLayout.LayoutParams(0,dp(52),1));b.addView(actions);
            signIn.setOnClickListener(v->{String e=val(cloudEmail),p=val(password),n=val(person);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){cloudEmail.setError("Valid email required");return;}if(p.isEmpty()){password.setError("Password required");return;}runCloud("Signing in…",()->{SupabaseClientLite.AuthResult ar=cloudSync.signIn(e,p);CloudSyncFoundation.WorkspaceMembership wm=cloudSync.firstWorkspace();return new Object[]{ar,wm};},obj->{Object[] r=(Object[])obj;SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)r[0];CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)r[1];accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(wm!=null)accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast(wm==null?"Signed in · create or accept a workspace":"Signed in to "+wm.name);showAccountWorkspace();});});
            signUp.setOnClickListener(v->{String e=val(cloudEmail),p=val(password),n=val(person);if(n.isEmpty()){person.setError("Your name required");return;}if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){cloudEmail.setError("Valid email required");return;}if(p.length()<6){password.setError("Use at least 6 characters");return;}runCloud("Creating account…",()->cloudSync.signUp(n,e,p),obj->{SupabaseClientLite.AuthResult ar=(SupabaseClientLite.AuthResult)obj;accountTeam.bindCloudAccount(ar.userId,n,ar.email);if(ar.signedIn){toast("Account created and signed in");showAccountWorkspace();}else new MaterialAlertDialogBuilder(this).setTitle("Confirm your email").setMessage("Supabase created the account. Open the confirmation email, confirm it, then return here and sign in with the same password.").setPositiveButton("OK",null).show();});});
            b.addView(paragraph("Fida Field remains fully usable offline without signing in. Cloud sign-in is required only for multi-device synchronization and team workspaces."));return;
        }
        b.addView(info("Signed-in account",cloudSync.accountEmail()));b.addView(info("User ID",cloudSync.userId()));
        MaterialButton refresh=outlineButton("Refresh workspace membership");refresh.setOnClickListener(v->runCloud("Checking memberships…",()->accountTeam.hasCloudWorkspace()?cloudSync.refreshWorkspaceAccess(accountTeam.workspaceId()):cloudSync.firstWorkspace(),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;if(wm==null){toast(accountTeam.hasCloudWorkspace()?"Workspace access is disabled or removed":"No cloud workspace membership found");}else{accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Workspace refreshed · "+wm.role);}if(workspaceAccessRevoked())showWorkspaceAccessBlocked();else showAccountWorkspace();}));b.addView(refresh);
        if(accountTeam.hasCloudWorkspace()){
            b.addView(section("Cloud workspace"));b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Workspace ID",accountTeam.workspaceId()));b.addView(info("Role",accountTeam.accountRole()));MaterialButton sync=button("Sync this workspace");sync.setOnClickListener(v->showCloudSync());b.addView(sync);
        }else{
            b.addView(section("Create or join workspace"));if(canManageWorkspaceSettings()){MaterialButton create=button("Create cloud workspace");create.setOnClickListener(v->{String name=val(workspace);if(name.isEmpty()){workspace.setError("Workspace name required");return;}runCloud("Creating cloud workspace…",()->cloudSync.createWorkspace(name),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Cloud workspace created");showAccountWorkspace();});});b.addView(create);}
            EditText invite=input("Invitation code","");b.addView(invite);MaterialButton accept=outlineButton("Accept invitation");accept.setOnClickListener(v->{String code=val(invite);if(code.isEmpty()){invite.setError("Invitation code required");return;}runCloud("Accepting invitation…",()->cloudSync.acceptInvite(code),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Joined "+wm.name);showAccountWorkspace();});});b.addView(accept);
        }
        MaterialButton signOut=outlineButton("Sign out of cloud");signOut.setOnClickListener(v->runCloud("Signing out…",()->{cloudSync.signOut();return null;},obj->{accountTeam.clearCloudBinding();toast("Cloud account signed out · local data remains available");showAccountWorkspace();}));b.addView(signOut);
    }

    private void showTeam(){
        if(!requireWorkspaceManager("Team administration"))return;
        setHeader("Team","Workspace members & invitations");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        if(!accountTeam.hasWorkspace()){b.addView(empty("Create your workspace before adding team members."));MaterialButton setup=button("Set up workspace");setup.setOnClickListener(v->showAccountWorkspace());b.addView(setup);return;}
        boolean cloud=accountTeam.hasCloudWorkspace()&&cloudSync.signedIn();b.addView(section(accountTeam.workspaceName()));b.addView(info("Your role",accountTeam.accountRole()));b.addView(info("Mode",cloud?"Cloud workspace · Supabase":"Local workspace"));
        if(cloud){MaterialButton refresh=outlineButton("Refresh team from cloud");refresh.setOnClickListener(v->runCloud("Refreshing team…",()->{cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{toast("Team refreshed");showPeopleTeam();}));b.addView(refresh);}
        if(accountTeam.canManageTeam()){MaterialButton invite=button("+ Invite member");invite.setOnClickListener(v->showInviteDialog());b.addView(invite);}else b.addView(paragraph("Only workspace Owners and Admins can manage members and invitations."));
        List<AppDatabase.Row> members=db.workspaceMembers(accountTeam.workspaceId());b.addView(section("Members ("+members.size()+")"));if(members.isEmpty())b.addView(empty(cloud?"Refresh the team to download workspace members.":"No members yet."));for(AppDatabase.Row r:members){String meta=(r.s("email").isEmpty()?"No email":r.s("email"))+" • "+r.s("status");MaterialCardView c=rowCard(r.s("name"),meta,r.s("role"));if(accountTeam.canManageTeam()&&!"Owner".equals(r.s("role")))c.setOnClickListener(v->showMemberDialog(r.id()));b.addView(c);}
        renderWorkspaceInvitations(b,cloud);
    }

    private void showInviteDialog(){showInviteDialog("",AccountTeamManager.ROLE_TECHNICIAN);}
    private void showInviteDialog(String prefillEmail,String defaultRole){
        if(!accountTeam.canManageTeam()){toast("Owner or Admin access required");return;}LinearLayout f=form();EditText email=input("Email address",prefillEmail==null?"":prefillEmail);Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});setSpinner(role,defaultRole==null?AccountTeamManager.ROLE_TECHNICIAN:defaultRole);f.addView(email);f.addView(label("Role"));f.addView(role);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Invite workspace member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Create invitation",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String e=val(email),r=String.valueOf(role.getSelectedItem());if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Valid email required");return;}if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){runCloud("Creating invitation…",()->{String token=cloudSync.createInvite(accountTeam.workspaceId(),e,r);cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return token;},obj->{d.dismiss();String token=String.valueOf(obj);toast(cloudSync.lastInviteEmailMessage());new MaterialAlertDialogBuilder(this).setTitle(cloudSync.lastInviteEmailSent()?"Invitation sent":"Invitation created").setMessage((cloudSync.lastInviteEmailSent()?"Email sent to "+e+". On Android, the recipient can tap ‘Open Fida Field & join’ and the invitation will load automatically. The code below is only a fallback.":"Email delivery was not confirmed. Share this fallback invitation code with "+e+".")+"\n\n"+token).setNegativeButton("Close",(a,b)->showPeopleTeam()).setPositiveButton("Copy code",(a,b)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",token));toast("Invitation code copied");showPeopleTeam();}).show();});}else{db.saveWorkspaceInvite(accountTeam.workspaceId(),e,r);d.dismiss();toast("Invitation saved locally");showPeopleTeam();}}));d.show();
    }

    private void showMemberDialog(long id){
        if(!requireWorkspaceManager("Team administration"))return;
        AppDatabase.Row r=db.getWorkspaceMember(id);if(r.id()==0)return;if("Owner".equals(r.s("role"))){toast("The workspace owner cannot be disabled or changed here");return;}LinearLayout f=form();EditText name=input("Name",r.s("name"));EditText email=input("Email",r.s("email"));name.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));email.setEnabled(!(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()));Spinner role=spinner(new String[]{AccountTeamManager.ROLE_ADMIN,AccountTeamManager.ROLE_TECHNICIAN,AccountTeamManager.ROLE_VIEWER});setSpinner(role,r.s("role"));MaterialSwitch enabled=new MaterialSwitch(this);enabled.setText("Workspace app access enabled");enabled.setChecked("Active".equalsIgnoreCase(r.s("status")));f.addView(name);f.addView(email);f.addView(label("Role"));f.addView(role);f.addView(section("Access"));f.addView(enabled);f.addView(paragraph("Disabled members keep their account and history but cannot access or synchronize this workspace until re-enabled."));AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Workspace member").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Name required");return;}String rr=String.valueOf(role.getSelectedItem()),ss=enabled.isChecked()?"Active":"Inactive";Runnable save=()->updateWorkspaceMemberAccess(r,rr,ss,()->{d.dismiss();toast(enabled.isChecked()?"Member enabled":"Member disabled");showPeopleTeam();});if(!enabled.isChecked()&&!"Inactive".equalsIgnoreCase(r.s("status"))){new MaterialAlertDialogBuilder(this).setTitle("Disable workspace access?").setMessage(r.s("name")+" will no longer be able to access or synchronize this workspace. Existing jobs and history are not deleted.").setNegativeButton("Keep enabled",null).setPositiveButton("Disable",(a,w)->save.run()).show();}else save.run();}));d.show();
    }

    private void updateWorkspaceMemberAccess(AppDatabase.Row member,String role,String status,Runnable success){
        if(accountTeam.hasCloudWorkspace()&&cloudSync.signedIn()){runCloud("Updating workspace access…",()->{cloudSync.updateMember(accountTeam.workspaceId(),member.s("member_uuid"),role,status);cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->success.run());}
        else{db.saveWorkspaceMember(member.id(),accountTeam.workspaceId(),member.s("name"),member.s("email"),role,status);success.run();}
    }

    private void showCloudSync(){
        CloudSyncWorker.configure(this,prefs.getBoolean(CloudSyncWorker.KEY_ENABLED,true));
        setHeader("Cloud & Team Sync","Reliable offline-first Supabase synchronization");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        b.addView(section("Workspace"));b.addView(info("Workspace",accountTeam.hasWorkspace()?accountTeam.workspaceName():"Not set up"));b.addView(info("Role",accountTeam.accountRole().isEmpty()?"Local user":accountTeam.accountRole()));b.addView(info("Cloud binding",accountTeam.hasCloudWorkspace()?"Bound":"Local only"));b.addView(info("Workspace access",workspaceAccessRevoked()?"Disabled":cloudSync.workspaceAccessState()));b.addView(info("Access checked",cloudSync.workspaceAccessCheckedAt()));
        b.addView(section("Supabase"));b.addView(info("Status",cloudSync.backendStatus()));b.addView(info("Account",cloudSync.accountEmail().isEmpty()?"Not signed in":cloudSync.accountEmail()));b.addView(info("Last sync",cloudSync.lastSync()));b.addView(info("Last result",cloudSync.lastResult()));
        b.addView(section("This device"));b.addView(info("Device ID",cloudSync.deviceId()));b.addView(info("Pending changes",String.valueOf(cloudSync.pendingChanges())));b.addView(info("Protected conflicts",String.valueOf(cloudSync.conflictCount())));b.addView(info("Last background sync",prefs.getString(CloudSyncWorker.KEY_LAST_RUN,"Never")));
        MaterialSwitch autoSync=new MaterialSwitch(this);autoSync.setText("Automatic cloud sync");autoSync.setChecked(prefs.getBoolean(CloudSyncWorker.KEY_ENABLED,true));autoSync.setOnCheckedChangeListener((button,checked)->{prefs.edit().putBoolean(CloudSyncWorker.KEY_ENABLED,checked).apply();CloudSyncWorker.configure(this,checked);toast(checked?"Automatic sync enabled":"Automatic sync disabled");});b.addView(autoSync);
        b.addView(paragraph("Queued offline edits are pushed before cloud data is applied. If another device changes the same record while this device still has unsynced work, Fida Field protects the local edit and records a conflict instead of silently overwriting it. Cloud deletions use tombstones so they propagate safely to other devices."));
        if(cloudSync.signedIn()&&accountTeam.hasCloudWorkspace()){MaterialButton accessCheck=outlineButton("Check workspace access");accessCheck.setOnClickListener(v->runCloud("Checking workspace access…",()->cloudSync.refreshWorkspaceAccess(accountTeam.workspaceId()),obj->{CloudSyncFoundation.WorkspaceMembership wm=(CloudSyncFoundation.WorkspaceMembership)obj;if(wm==null){toast("Workspace access is disabled");showWorkspaceAccessBlocked();}else{accountTeam.bindCloudWorkspace(wm.id,wm.name,wm.role);toast("Access active · "+wm.role);showCloudSync();}}));b.addView(accessCheck);}
        MaterialButton sync=button("Sync now");sync.setEnabled(cloudSync.backendConfigured()&&cloudSync.signedIn()&&accountTeam.hasCloudWorkspace()&&!workspaceAccessRevoked());sync.setOnClickListener(v->runCloud("Synchronizing workspace…",()->cloudSync.syncNow(accountTeam.workspaceId(),accountTeam.canManageTeam()),obj->{CloudSyncFoundation.SyncResult r=(CloudSyncFoundation.SyncResult)obj;refreshEntitlementsAndBranding();toast(r.message);recreate();}));b.addView(sync);
        if(!cloudSync.signedIn()||!accountTeam.hasCloudWorkspace()){b.addView(paragraph("Sign in and bind a cloud workspace under Account & Workspace before synchronization can run."));MaterialButton account=outlineButton("Open Account & Workspace");account.setOnClickListener(v->showAccountWorkspace());b.addView(account);}else{MaterialButton team=outlineButton("Refresh team only");team.setOnClickListener(v->runCloud("Refreshing team…",()->{cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{toast("Team refreshed");showCloudSync();}));b.addView(team);}
        MaterialButton copy=outlineButton("Copy device ID");copy.setOnClickListener(v->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field device ID",cloudSync.deviceId()));toast("Device ID copied");});b.addView(copy);
    }

    private void showUpgradeRequired(String feature){
        new MaterialAlertDialogBuilder(this).setTitle(feature+" requires Pro").setMessage("The Free plan includes "+EntitlementManager.FREE_MONTHLY_REPORT_LIMIT+" new service reports per month. Pro unlocks unlimited reports, CSV exports, custom company branding and the AI report assistant. Use More → Plan & subscription to subscribe the company workspace. Fidalix Open builds are enabled internally without Google Play Billing.").setNegativeButton("Not now",null).setPositiveButton("View plan",(d,w)->showPlan()).show();
    }

    private void showSettings(){
        if(!requireWorkspaceManager("Company settings"))return;
        setHeader("Settings","Company identity & application preferences");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        EditText company=input("Company name",prefs.getString("company_name","Fidalix Limited"));Spinner tech=choiceSpinner(technicianChoices(true,prefs.getString("technician_name","")));setChoiceByLabel(tech,prefs.getString("technician_name",""));EditText phone=input("Company phone",prefs.getString("company_phone",""));EditText email=input("Company email",prefs.getString("company_email",""));EditText addr=input("Company address",prefs.getString("company_address","Kigali, Rwanda"));EditText prefix=input("Report prefix",prefs.getString("report_prefix","FSR"));Spinner theme=spinner(new String[]{"System","Light","Dark"});setSpinner(theme,prefs.getString("theme","System"));MaterialSwitch reminders=new MaterialSwitch(this);reminders.setText("Maintenance reminder notifications");reminders.setChecked(prefs.getBoolean("maintenance_notifications",true));EditText reminderDays=input("Notify this many days before service",prefs.getString("maintenance_reminder_days","14"));reminderDays.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        b.addView(section("Business profile"));b.addView(company);b.addView(label("Default technician"));b.addView(tech);b.addView(phone);b.addView(email);b.addView(addr);b.addView(prefix);b.addView(label("Theme"));b.addView(theme);b.addView(section("Maintenance reminders"));b.addView(reminders);b.addView(reminderDays);
        MaterialButton save=button("Save settings");save.setOnClickListener(v->{Choice tc=(Choice)tech.getSelectedItem();String techName=tc==null||tc.id==0?"":tc.label;prefs.edit().putString("company_name",val(company)).putString("technician_name",techName).putString("company_phone",val(phone)).putString("company_email",val(email)).putString("company_address",val(addr)).putString("report_prefix",val(prefix)).putString("theme",String.valueOf(theme.getSelectedItem())).putBoolean("maintenance_notifications",reminders.isChecked()).putString("maintenance_reminder_days",val(reminderDays).isEmpty()?"14":val(reminderDays)).apply();if(reminders.isChecked())requestNotificationPermissionIfNeeded();scheduleMaintenanceReminders();toast("Settings saved");applyThemeMode(String.valueOf(theme.getSelectedItem()));recreate();});b.addView(save);
        MaterialButton check=outlineButton("Check maintenance reminders now");check.setOnClickListener(v->{requestNotificationPermissionIfNeeded();MaintenanceReminderWorker.notifyNow(this);});b.addView(check);
        b.addView(section("Testing"));MaterialButton demo=outlineButton("Load demo customer & asset");demo.setOnClickListener(v->{db.insertDemoData();toast("Demo data ready");showDashboard();});b.addView(demo);
    }

    private void showCustomerDialog(long id){
        if(!requireWorkspaceManager("Customer master data"))return;
        AppDatabase.Row r=id>0?db.getCustomer(id):new AppDatabase.Row();LinearLayout form=form();EditText name=input("Customer / company name *",r.s("name"));EditText contact=input("Primary contact",r.s("contact"));EditText phone=input("Phone",r.s("phone"));EditText email=input("Email",r.s("email"));EditText address=input("Address",r.s("address"));EditText notes=multi("Notes",r.s("notes"));form.addView(name);form.addView(contact);form.addView(phone);form.addView(email);form.addView(address);form.addView(notes);
        MaterialAlertDialogBuilder d=new MaterialAlertDialogBuilder(this).setTitle(id>0?"Edit customer":"New customer").setView(scrollForm(form)).setNegativeButton("Cancel",null).setPositiveButton("Save",null);if(id>0)d.setNeutralButton("Add site",(x,w)->showSiteDialog(0,id));AlertDialog dialog=d.create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Required");return;}Map<String,String> m=AppDatabase.map("name",val(name),"contact",val(contact),"phone",val(phone),"email",val(email),"address",val(address),"notes",val(notes));db.saveCustomer(id,m);dialog.dismiss();toast("Customer saved");refreshCurrent();}));dialog.show();
    }

    private void showSiteDialog(long id,long preferredCustomer){
        if(!requireWorkspaceManager("Site master data"))return;
        AppDatabase.Row r=id>0?db.getSite(id):new AppDatabase.Row();List<Choice> customers=customerChoices(true);LinearLayout form=form();Spinner customer=choiceSpinner(customers);long cid=id>0?parse(r.s("customer_id")):preferredCustomer;setChoice(customer,cid);EditText name=input("Site name *",r.s("name"));EditText address=input("Address",r.s("address"));EditText contact=input("Site contact",r.s("contact"));EditText phone=input("Phone",r.s("phone"));EditText notes=multi("Notes",r.s("notes"));form.addView(label("Customer *"));form.addView(customer);form.addView(name);form.addView(address);form.addView(contact);form.addView(phone);form.addView(notes);
        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle(id>0?"Edit site":"New site").setView(scrollForm(form)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{Choice ch=(Choice)customer.getSelectedItem();if(ch==null||ch.id==0){toast("Add/select a customer first");return;}if(val(name).isEmpty()){name.setError("Required");return;}db.saveSite(id,AppDatabase.map("customer_id",String.valueOf(ch.id),"name",val(name),"address",val(address),"contact",val(contact),"phone",val(phone),"notes",val(notes)));dialog.dismiss();toast("Site saved");refreshCurrent();}));dialog.show();
    }

    private void showAssetDialog(long id){
        if(!requireWorkspaceManager("Asset master data"))return;
        AppDatabase.Row r=id>0?db.getAsset(id):new AppDatabase.Row();LinearLayout form=form();Spinner customer=choiceSpinner(customerChoices(true));setChoice(customer,parse(r.s("customer_id")));Spinner site=choiceSpinner(siteChoices(true));setChoice(site,parse(r.s("site_id")));EditText tag=input("Asset tag *",id>0?r.s("tag"):db.nextAssetTag());EditText name=input("Asset name *",r.s("name"));EditText category=input("Category",r.s("category"));EditText model=input("Make / model",r.s("make_model"));EditText serial=input("Serial number",r.s("serial"));EditText location=input("Location",r.s("location"));EditText interval=input("Maintenance interval (days)",r.s("interval_days"));interval.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);EditText next=input("Next service date (YYYY-MM-DD)",r.s("next_service"));next.setFocusable(false);next.setOnClickListener(v->pickDate(next));EditText notes=multi("Notes",r.s("notes"));form.addView(label("Customer"));form.addView(customer);form.addView(label("Site"));form.addView(site);form.addView(tag);form.addView(name);form.addView(category);form.addView(model);form.addView(serial);form.addView(location);form.addView(interval);form.addView(next);form.addView(notes);if(id>0){MaterialButton qr=outlineButton("Show / share asset QR");qr.setOnClickListener(v->showAssetQr(r));form.addView(qr);}
        MaterialAlertDialogBuilder builder=new MaterialAlertDialogBuilder(this).setTitle(id>0?"Edit asset":"Add asset").setView(scrollForm(form)).setNegativeButton("Cancel",null).setPositiveButton("Save",null);if(id>0)builder.setNeutralButton("Create job",(d,w)->showJobDialog(0,id));AlertDialog dialog=builder.create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(tag).isEmpty()||val(name).isEmpty()){toast("Asset tag and name are required");return;}Choice c=(Choice)customer.getSelectedItem(),s=(Choice)site.getSelectedItem();try{db.saveAsset(id,AppDatabase.map("customer_id",String.valueOf(c==null?0:c.id),"site_id",String.valueOf(s==null?0:s.id),"tag",val(tag),"name",val(name),"category",val(category),"make_model",val(model),"serial",val(serial),"location",val(location),"interval_days",val(interval),"next_service",val(next),"notes",val(notes)));dialog.dismiss();toast("Asset saved");refreshCurrent();}catch(Exception e){error("Could not save asset",e);}}));dialog.show();
    }

    private void showJobDialog(long id,long preferredAsset){
        if(!canPerformFieldWork()){new MaterialAlertDialogBuilder(this).setTitle("Read-only access").setMessage("Viewer accounts can review available service information but cannot create or modify jobs.").setPositiveButton("OK",null).show();return;}
        if(id==0&&!entitlements.canCreateReport()){showUpgradeRequired("More service reports");return;}
        AppDatabase.Row r=id>0?db.getJob(id):new AppDatabase.Row();
        if(id>0&&!canSeeJob(r)){new MaterialAlertDialogBuilder(this).setTitle("Job not available").setMessage("You can only access service jobs assigned to your workspace person profile.").setPositiveButton("OK",null).show();return;}
        if(id>0&&"Completed".equals(r.s("status"))&&!accountTeam.canManageTeam()){new MaterialAlertDialogBuilder(this).setTitle("Completed job locked").setMessage("Only an Owner or Admin can modify a completed service job.").setPositiveButton("OK",null).show();return;}
        boolean manager=canSeeAllJobs();long ownTech=myTechnicianId();if(id==0&&!manager&&ownTech<=0){new MaterialAlertDialogBuilder(this).setTitle("Field assignment required").setMessage("Your workspace account is not linked to an active field person. Ask an Owner or Admin to enable field job assignment for your People & Team profile.").setPositiveButton("OK",null).show();return;}
        AppDatabase.Row ar=preferredAsset>0?db.getAsset(preferredAsset):new AppDatabase.Row();LinearLayout form=form();Spinner customer=choiceSpinner(customerChoices(true));long customerId=id>0?parse(r.s("customer_id")):parse(ar.s("customer_id"));setChoice(customer,customerId);Spinner site=choiceSpinner(siteChoices(true));long siteId=id>0?parse(r.s("site_id")):parse(ar.s("site_id"));setChoice(site,siteId);Spinner asset=choiceSpinner(assetChoices(true));long assetId=id>0?parse(r.s("asset_id")):preferredAsset;setChoice(asset,assetId);EditText jobTitle=input("Job title *",r.s("title"));EditText problem=multi("Reported problem",r.s("problem"));EditText diagnosis=multi("Diagnosis",r.s("diagnosis"));EditText work=multi("Work performed",r.s("work_done"));EditText parts=multi("Parts / materials",r.s("parts"));String currentTech=id>0?r.s("technician"):prefs.getString("technician_name","");long currentTechId=id>0?parse(r.s("technician_id")):(manager?0:ownTech);List<Choice> jobTechChoices;if(manager)jobTechChoices=technicianChoices(true,currentTech);else{jobTechChoices=new ArrayList<>();AppDatabase.Row me=db.getTechnician(ownTech);jobTechChoices.add(new Choice(ownTech,me.s("name")));}Spinner tech=choiceSpinner(jobTechChoices);if(currentTechId>0)setChoice(tech,currentTechId);else setChoiceByLabel(tech,currentTech);tech.setEnabled(manager);Spinner priority=spinner(new String[]{"Low","Normal","High","Urgent"});setSpinner(priority,id>0?r.s("priority"):"Normal");Spinner status=spinner(new String[]{"Open","In Progress","Completed","Cancelled"});setSpinner(status,id>0?r.s("status"):"Open");EditText date=input("Service date",id>0?r.s("job_date"):db.today());date.setFocusable(false);date.setOnClickListener(v->pickDate(date));EditText next=input("Next recommended service",id>0?r.s("next_service"):ar.s("next_service"));next.setFocusable(false);next.setOnClickListener(v->pickDate(next));form.addView(label("Customer"));form.addView(customer);form.addView(label("Site"));form.addView(site);form.addView(label("Asset"));form.addView(asset);form.addView(jobTitle);form.addView(problem);form.addView(diagnosis);form.addView(work);form.addView(parts);MaterialButton checklist=outlineButton("Service checklist");checklist.setOnClickListener(v->showServiceChecklist(work));form.addView(checklist);MaterialButton aiAssist=outlineButton("AI assist report");aiAssist.setOnClickListener(v->showAiReportAssistant(jobTitle,problem,diagnosis,work,parts));form.addView(aiAssist);form.addView(label("Technician"));form.addView(tech);form.addView(label("Priority"));form.addView(priority);form.addView(label("Status"));form.addView(status);form.addView(date);form.addView(next);
        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle(id>0?"Edit service job":"New service job").setView(scrollForm(form)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(jobTitle).isEmpty()){jobTitle.setError("Required");return;}Choice c=(Choice)customer.getSelectedItem(),s=(Choice)site.getSelectedItem(),a=(Choice)asset.getSelectedItem();Map<String,String> m=AppDatabase.map("customer_id",String.valueOf(c==null?0:c.id),"site_id",String.valueOf(s==null?0:s.id),"asset_id",String.valueOf(a==null?0:a.id),"title",val(jobTitle),"problem",val(problem),"diagnosis",val(diagnosis),"work_done",val(work),"parts",val(parts),"technician",choiceLabel(tech),"technician_id",String.valueOf(((Choice)tech.getSelectedItem()).id),"assignment_actor",accountTeam.accountName(),"priority",String.valueOf(priority.getSelectedItem()),"status",String.valueOf(status.getSelectedItem()),"job_date",val(date),"next_service",val(next),"customer_name_signed",id>0?r.s("customer_name_signed"):"");try{long saved=db.saveJob(id,m,prefs.getString("report_prefix","FSR"));if("Completed".equals(String.valueOf(status.getSelectedItem()))&&a!=null&&a.id>0){String ns=val(next);if(ns.isEmpty())ns=db.suggestNextService(a.id,val(date));db.completeMaintenanceIfNeeded(a.id,saved,val(work),ns);}dialog.dismiss();toast("Job saved");showJobDetail(saved);}catch(Exception e){error("Could not save job",e);}}));dialog.show();
    }

    private void showServiceChecklist(EditText work){
        String[] types={"Preventive maintenance","Corrective maintenance","Installation / commissioning","Inspection / site survey"};
        new MaterialAlertDialogBuilder(this).setTitle("Service checklist").setMessage("Choose a checklist. Only tick actions you actually performed; selected items are added to Work performed and remain editable.").setItems(types,(d,which)->{
            if(which==0)showServiceChecklistItems("Preventive maintenance",new String[]{"Visual condition inspected","Connections and cabling checked","Equipment cleaned or housekeeping completed","Operational test completed","Alarms and indicators checked","Maintenance findings recorded"},work);
            else if(which==1)showServiceChecklistItems("Corrective maintenance",new String[]{"Fault symptoms verified","Fault source isolated","Repair or replacement completed","Connections restored and secured","Operational test completed","Final operating condition verified"},work);
            else if(which==2)showServiceChecklistItems("Installation / commissioning",new String[]{"Equipment installed or mounted","Power and cabling connected","Configuration completed","Network or service connectivity tested","Functional test completed","Labelling or handover completed"},work);
            else showServiceChecklistItems("Inspection / site survey",new String[]{"Physical condition inspected","Power and environment checked","Cabling and connections inspected","Configuration or status reviewed","Findings documented","Recommendations recorded"},work);
        }).setNegativeButton("Cancel",null).show();
    }

    private void showServiceChecklistItems(String type,String[] items,EditText work){
        boolean[] checked=new boolean[items.length];
        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle(type).setMultiChoiceItems(items,checked,(d,which,isChecked)->checked[which]=isChecked).setNegativeButton("Cancel",null).setPositiveButton("Add selected",null).create();
        dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            ArrayList<String> selected=new ArrayList<>();for(int i=0;i<items.length;i++)if(checked[i])selected.add(items[i]);
            if(selected.isEmpty()){toast("Select at least one completed action");return;}
            String current=val(work);StringBuilder add=new StringBuilder();for(String item:selected){String line="✓ "+item;if(!current.contains(line))add.append(line).append("\n");}
            if(add.length()==0){toast("Selected actions are already listed");dialog.dismiss();return;}
            String block="Checklist confirmed · "+type+"\n"+add.toString().trim();work.setText(current.isEmpty()?block:current+"\n\n"+block);work.setSelection(work.getText().length());dialog.dismiss();toast(selected.size()+" checklist item"+(selected.size()==1?"":"s")+" added");
        }));dialog.show();
    }

    private void showAiReportAssistant(EditText jobTitle,EditText problem,EditText diagnosis,EditText work,EditText parts){
        if(!entitlements.canUseAiReportAssistant()){showUpgradeRequired("AI report assistant");return;}
        if(accountTeam==null||!accountTeam.hasWorkspace()||!cloudSync.signedIn()){new MaterialAlertDialogBuilder(this).setTitle("Cloud sign-in required").setMessage("AI report assist uses the secure Fida Field cloud service. Sign in and connect a workspace first.").setNegativeButton("Cancel",null).setPositiveButton("Open account",(d,w)->showAccountWorkspace()).show();return;}
        if(val(problem).isEmpty()&&val(diagnosis).isEmpty()&&val(work).isEmpty()&&val(parts).isEmpty()){toast("Enter some service notes first");return;}
        toast("Preparing AI report suggestion…");new Thread(()->{try{JSONObject draft=cloudSync.aiReportDraft(accountTeam.workspaceId(),val(jobTitle),val(problem),val(diagnosis),val(work),val(parts));runOnUiThread(()->showAiReportDraftReview(diagnosis,work,parts,draft));}catch(Exception e){String msg=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();runOnUiThread(()->new MaterialAlertDialogBuilder(this).setTitle("AI assistant unavailable").setMessage(msg).setPositiveButton("OK",null).show());}}).start();
    }

    private void showAiReportDraftReview(EditText diagnosis,EditText work,EditText parts,JSONObject draft){
        String d=draft.optString("diagnosis","").trim(),w=draft.optString("work_done","").trim(),p=draft.optString("parts","").trim();if(d.isEmpty())d=val(diagnosis);if(w.isEmpty())w=val(work);if(p.isEmpty())p=val(parts);
        LinearLayout f=form();f.addView(paragraph("Review the suggestion before applying it. AI improves wording only; verify every technical fact."));EditText dEdit=multi("Diagnosis",d);EditText wEdit=multi("Work performed",w);EditText pEdit=multi("Parts / materials",p);f.addView(dEdit);f.addView(wEdit);f.addView(pEdit);
        AlertDialog dialog=new MaterialAlertDialogBuilder(this).setTitle("AI report suggestion").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Apply",null).create();dialog.setOnShowListener(x->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{diagnosis.setText(val(dEdit));work.setText(val(wEdit));parts.setText(val(pEdit));dialog.dismiss();toast("AI wording applied · review before saving");}));dialog.show();
    }

    private void showJobDetail(long id){
        AppDatabase.Row j=db.getJob(id);if(j.id()==0){toast("Job not found");return;}if(!canSeeJob(j)){toast("This job is not assigned to you");showJobs();return;}setHeader(j.s("report_no"),j.s("status"));clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Jobs");back.setOnClickListener(v->showJobs());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));top.addView(spacerH());boolean completed="Completed".equals(j.s("status"));boolean canModify=canPerformFieldWork()&&(!completed||accountTeam.canManageTeam());if(canModify){MaterialButton edit=button("Edit");edit.setOnClickListener(v->showJobDialog(id,0));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);if(completed&&!canModify)b.addView(empty("Locked — only an Owner or Admin can modify this completed service job."));
        b.addView(section(j.s("title")));b.addView(info("Customer",j.s("customer_name")));b.addView(info("Site",j.s("site_name")));b.addView(info("Asset",(j.s("asset_tag").isEmpty()?"":j.s("asset_tag")+" · ")+j.s("asset_name")));b.addView(info("Service date",j.s("job_date")));b.addView(info("Technician",j.s("technician")));if(canSeeAllJobs())b.addView(info("Assignment control","Owner/Admin · reassignment allowed"));b.addView(info("Priority",j.s("priority")));
        addIf(b,"Reported problem",j.s("problem"));addIf(b,"Diagnosis",j.s("diagnosis"));addIf(b,"Work performed",j.s("work_done"));addIf(b,"Parts / materials",j.s("parts"));addIf(b,"Next service",j.s("next_service"));
        b.addView(section("Assignment history"));List<AppDatabase.Row> assignmentHistory=db.assignmentHistory(id);if(assignmentHistory.isEmpty())b.addView(paragraph("No reassignment recorded yet."));else for(AppDatabase.Row h:assignmentHistory){String from=h.s("from_technician_name").isEmpty()?"Unassigned":h.s("from_technician_name");String to=h.s("to_technician_name").isEmpty()?"Unassigned":h.s("to_technician_name");String meta=h.s("changed_at")+(h.s("changed_by").isEmpty()?"":" • "+h.s("changed_by"));b.addView(rowCard(from+" → "+to,meta,h.i("pending")==1?"Pending sync":"Recorded"));}
        b.addView(section("Evidence & acceptance"));b.addView(info("Photos",db.photos(id).size()+" attached"));b.addView(info("Signature",j.s("signature_path").isEmpty()?"Not captured":"Captured by "+j.s("customer_name_signed")));
        if(canModify){LinearLayout a=new LinearLayout(this);a.setOrientation(LinearLayout.HORIZONTAL);MaterialButton photo=outlineButton("Add photo");photo.setOnClickListener(v->capturePhoto(id));a.addView(photo,new LinearLayout.LayoutParams(0,dp(50),1));a.addView(spacerH());MaterialButton sig=outlineButton("Signature");sig.setOnClickListener(v->captureSignature(id));a.addView(sig,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(a);}else b.addView(paragraph("Photos and customer signature are locked with the completed job. Ask an Owner or Admin if a correction is required."));
        b.addView(section("Actions"));if(canSeeAllJobs()){MaterialButton reassign=outlineButton("Reassign job");reassign.setOnClickListener(v->showReassignJob(id));b.addView(reassign);}MaterialButton pdf=button("Generate & share PDF");pdf.setOnClickListener(v->generateAndShare(id));b.addView(pdf);if(canModify&&!"Completed".equals(j.s("status"))){MaterialButton complete=outlineButton("Mark job completed");complete.setOnClickListener(v->{long aid=parse(j.s("asset_id"));String ns=j.s("next_service");if(aid>0&&ns.isEmpty())ns=db.suggestNextService(aid,j.s("job_date"));db.setJobStatus(id,"Completed");if(aid>0)db.completeMaintenanceIfNeeded(aid,id,j.s("work_done"),ns);toast(ns.isEmpty()?"Job completed":"Job completed • next service "+ns);showJobDetail(id);});b.addView(complete);}else{b.addView(info("Status","Completed — ready for final reporting"));}
    }

    private void showReassignJob(long jobId){if(!canSeeAllJobs()){toast("Only Owner or Admin can reassign jobs");return;}AppDatabase.Row job=db.getJob(jobId);if(job.id()==0)return;ArrayList<Choice> choices=new ArrayList<>();for(AppDatabase.Row t:db.activeTechnicians())choices.add(new Choice(t.id(),t.s("name")+(t.s("user_uuid").isEmpty()?" · field only":" · app member")));if(choices.isEmpty()){toast("No active field people available");return;}LinearLayout f=form();Spinner tech=choiceSpinner(choices);setChoice(tech,parse(job.s("technician_id")));f.addView(label("Assign to"));f.addView(tech);f.addView(paragraph("The previous and new assignee are retained in Assignment history. The previous assignee loses access after cloud synchronization; the new assignee receives the job on their next sync."));AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Reassign "+job.s("report_no")).setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Reassign",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{Choice selected=(Choice)tech.getSelectedItem();if(selected==null||selected.id<=0)return;if(selected.id==parse(job.s("technician_id"))){toast("Job is already assigned to this person");return;}db.reassignJob(jobId,selected.id,accountTeam.accountName().isEmpty()?accountTeam.accountEmail():accountTeam.accountName());d.dismiss();toast("Job reassigned · queued for sync");showJobDetail(jobId);}));d.show();}

    private void capturePhoto(long jobId){
        if(ContextCompat.checkSelfPermission(this,Manifest.permission.CAMERA)!=android.content.pm.PackageManager.PERMISSION_GRANTED){
            photoJobId=jobId;cameraPermissionLauncher.launch(Manifest.permission.CAMERA);return;
        }
        launchCameraCapture(jobId);
    }

    private void launchCameraCapture(long jobId){
        Uri uri=null;
        try{
            ContentValues values=new ContentValues();values.put(MediaStore.Images.Media.DISPLAY_NAME,"FidaField-"+System.currentTimeMillis()+".jpg");values.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");
            if(Build.VERSION.SDK_INT>=29)values.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/FidaField");
            uri=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);if(uri==null)throw new Exception("Could not create photo destination");
            Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);intent.putExtra(MediaStore.EXTRA_OUTPUT,uri);intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);photoJobId=jobId;pendingPhotoUri=uri;cameraLauncher.launch(intent);
        }catch(Exception e){
            if(uri!=null)try{getContentResolver().delete(uri,null,null);}catch(Exception ignored){}pendingPhotoUri=null;photoJobId=0;error("Camera unavailable",e);
        }
    }

    private void showCameraPermissionRequired(){
        new MaterialAlertDialogBuilder(this).setTitle("Camera permission required").setMessage("Fida Field needs camera access to take job photos. Allow Camera permission, then try Add photo again.")
                .setNegativeButton("Cancel",null).setPositiveButton("Open app settings",(d,w)->{Intent i=new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName()));startActivity(i);}).show();
    }

    private void captureSignature(long jobId){
        LinearLayout form=form();EditText signer=input("Customer / representative name",db.getJob(jobId).s("customer_name_signed"));SignatureView sig=new SignatureView(this);form.addView(signer);form.addView(sig,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(230)));MaterialButton clear=outlineButton("Clear signature");clear.setOnClickListener(v->sig.clear());form.addView(clear);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Customer signature").setView(scrollForm(form)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(signer).isEmpty()){signer.setError("Signer name required");return;}if(sig.isEmpty()){toast("Please sign in the box");return;}try{File dir=new File(getFilesDir(),"signatures");if(!dir.exists())dir.mkdirs();File file=new File(dir,"job_"+jobId+"_"+System.currentTimeMillis()+".png");Bitmap bm=sig.bitmap();try(FileOutputStream out=new FileOutputStream(file)){bm.compress(Bitmap.CompressFormat.PNG,100,out);}bm.recycle();db.setSignature(jobId,file.getAbsolutePath(),val(signer));d.dismiss();toast("Signature saved");showJobDetail(jobId);}catch(Exception e){error("Could not save signature",e);}}));d.show();
    }

    private void showPeopleTeam(){
        if(!requireWorkspaceManager("People & Team"))return;
        setHeader("People & Team","One person · job assignment · app access");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);
        b.addView(paragraph("Each person is shown once. Job assignment and workspace/app access are separate capabilities: a contractor can be field-only with no app, while a signed-in member can optionally be made available for field jobs."));
        if(accountTeam.hasWorkspace())db.autoLinkPeople(accountTeam.workspaceId());
        boolean cloud=accountTeam.hasCloudWorkspace()&&cloudSync.signedIn();
        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);MaterialButton add=button("+ Field-only person");add.setOnClickListener(v->showUnifiedPerson(0,0));actions.addView(add,new LinearLayout.LayoutParams(0,dp(52),1));if(accountTeam.hasWorkspace()&&accountTeam.canManageTeam()){actions.addView(spacerH());MaterialButton invite=outlineButton("+ App access");invite.setOnClickListener(v->showInviteDialog());actions.addView(invite,new LinearLayout.LayoutParams(0,dp(52),1));}b.addView(actions);
        if(accountTeam.hasWorkspace()){b.addView(info("Workspace",accountTeam.workspaceName()));b.addView(info("Your access role",accountTeam.accountRole()));if(cloud){MaterialButton refresh=outlineButton("Refresh people & access");refresh.setOnClickListener(v->runCloud("Refreshing people…",()->{cloudSync.refreshTeamCache(accountTeam.workspaceId(),accountTeam.canManageTeam());return null;},obj->{db.autoLinkPeople(accountTeam.workspaceId());toast("People refreshed");showPeopleTeam();}));b.addView(refresh);}}

        b.addView(section("People"));
        java.util.HashSet<Long> shownTechs=new java.util.HashSet<>();int shown=0;
        if(accountTeam.hasWorkspace()){
            for(AppDatabase.Row m:db.workspaceMembers(accountTeam.workspaceId())){AppDatabase.Row tech=db.technicianForUser(m.s("user_uuid"));if(tech.id()>0)shownTechs.add(tech.id());String field=tech.id()>0?(tech.i("active")==1?"Field active":"Field inactive"):"Not assigned to field jobs";String detail=tech.id()>0?(tech.s("role").isEmpty()?"Field technician":tech.s("role"))+(tech.s("phone").isEmpty()?"":" • "+tech.s("phone")):(m.s("email").isEmpty()?"Workspace member":m.s("email"));String appState="Active".equalsIgnoreCase(m.s("status"))?"App active":"App disabled";MaterialCardView c=rowCard(m.s("name"),detail,m.s("role")+" · "+appState+" · "+field);long mid=m.id(),tid=tech.id();c.setOnClickListener(v->showUnifiedPerson(mid,tid));b.addView(c);shown++;}
        }
        for(AppDatabase.Row tech:db.technicians()){if(shownTechs.contains(tech.id()))continue;AppDatabase.Row linked=accountTeam.hasWorkspace()?db.workspaceMemberForUser(accountTeam.workspaceId(),tech.s("user_uuid")):new AppDatabase.Row();if(linked.id()>0)continue;String detail=(tech.s("role").isEmpty()?"Field technician":tech.s("role"))+(tech.s("email").isEmpty()?"":" • "+tech.s("email"))+(tech.s("phone").isEmpty()?"":" • "+tech.s("phone"));MaterialCardView c=rowCard(tech.s("name"),detail,"No app access · "+(tech.i("active")==1?"Field active":"Field inactive"));long tid=tech.id();c.setOnClickListener(v->showUnifiedPerson(0,tid));b.addView(c);shown++;}
        if(shown==0)b.addView(empty("No people yet. Add a field-only person or invite someone who needs app access."));

        if(accountTeam.hasWorkspace())renderWorkspaceInvitations(b,cloud);
    }

    private void renderWorkspaceInvitations(LinearLayout b,boolean cloud){
        List<AppDatabase.Row> all=db.workspaceInvites(accountTeam.workspaceId());ArrayList<AppDatabase.Row> pending=new ArrayList<>(),history=new ArrayList<>();int cancelled=0;
        for(AppDatabase.Row r:all){String status=r.s("status");if("Pending".equalsIgnoreCase(status))pending.add(r);else{history.add(r);if("Cancelled".equalsIgnoreCase(status))cancelled++;}}
        b.addView(section("Pending app invitations ("+pending.size()+")"));
        if(pending.isEmpty())b.addView(empty("No pending invitations."));
        for(AppDatabase.Row r:pending){MaterialCardView c=rowCard(r.s("email"),r.s("role"),"Pending");c.setOnClickListener(v->{String code=r.s("token");MaterialAlertDialogBuilder d=new MaterialAlertDialogBuilder(this).setTitle("Pending invitation").setMessage(r.s("email")+" · "+r.s("role")+(code.isEmpty()?"":"\n\nInvitation code:\n"+code)+(r.s("expires_at").isEmpty()?"":"\nExpires: "+r.s("expires_at"))).setNegativeButton("Close",null);if(!code.isEmpty())d.setNeutralButton("Copy code",(x,w)->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);cm.setPrimaryClip(android.content.ClipData.newPlainText("Fida Field invitation",code));toast("Invitation code copied");});if(accountTeam.canManageTeam())d.setPositiveButton("Cancel invitation",(x,w)->{if(cloud)runCloud("Cancelling invitation…",()->{cloudSync.cancelInvite(r.s("invite_uuid"));cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return null;},z->{toast("Invitation cancelled");showPeopleTeam();});else{db.cancelWorkspaceInvite(r.id());showPeopleTeam();}});d.show();});b.addView(c);}
        b.addView(section("Invitation history ("+history.size()+")"));
        if(history.isEmpty())b.addView(empty("No accepted, cancelled or expired invitations yet."));
        else for(AppDatabase.Row r:history)b.addView(rowCard(r.s("email"),r.s("role"),r.s("status")));
        if(cancelled>0&&accountTeam.canManageTeam()){final int cancelledCount=cancelled;MaterialButton clearCancelled=outlineButton("Clear cancelled ("+cancelledCount+")");clearCancelled.setOnClickListener(v->new MaterialAlertDialogBuilder(this).setTitle("Remove cancelled invitations?").setMessage("This permanently removes "+cancelledCount+" cancelled invitation record"+(cancelledCount==1?"":"s")+". Accepted invitation history is kept.").setNegativeButton("Keep",null).setPositiveButton("Clear",(d,w)->{if(cloud)runCloud("Clearing cancelled invitations…",()->{cloudSync.clearCancelledInvites(accountTeam.workspaceId());cloudSync.refreshTeamCache(accountTeam.workspaceId(),true);return null;},z->{toast("Cancelled invitations cleared");showPeopleTeam();});else{int removed=db.clearCancelledWorkspaceInvites(accountTeam.workspaceId());toast(removed+" cancelled invitation"+(removed==1?"":"s")+" cleared");showPeopleTeam();}}).show());b.addView(clearCancelled);}
    }

    private void showUnifiedPerson(long memberId,long technicianId){
        if(!requireWorkspaceManager("People & Team"))return;
        AppDatabase.Row member=memberId>0?db.getWorkspaceMember(memberId):new AppDatabase.Row();AppDatabase.Row tech=technicianId>0?db.getTechnician(technicianId):new AppDatabase.Row();boolean hasMember=member.id()>0,hasTech=tech.id()>0;
        LinearLayout f=form();String personName=hasTech?tech.s("name"):member.s("name");String personEmail=hasTech&&!tech.s("email").isEmpty()?tech.s("email"):member.s("email");EditText name=input("Person name *",personName);EditText fieldRole=input("Field role / job title",hasTech?tech.s("role"):"");EditText phone=input("Phone",hasTech?tech.s("phone"):"");EditText email=input("Email",personEmail);MaterialSwitch field=new MaterialSwitch(this);field.setText("Available for field job assignment");field.setChecked(hasTech&&tech.i("active")==1);f.addView(name);f.addView(fieldRole);f.addView(phone);f.addView(email);f.addView(field);
        final MaterialSwitch appAccess=hasMember&&accountTeam.canManageTeam()&&!"Owner".equals(member.s("role"))?new MaterialSwitch(this):null;
        if(hasMember){f.addView(section("Workspace access"));f.addView(info("Access role",member.s("role")));if(appAccess!=null){appAccess.setText("Workspace app access enabled");appAccess.setChecked("Active".equalsIgnoreCase(member.s("status")));f.addView(appAccess);f.addView(paragraph("Turn this off to suspend this member's workspace access without deleting their account, service history or assignments. It can be enabled again later."));MaterialButton access=outlineButton("Change access role");access.setOnClickListener(v->showMemberDialog(memberId));f.addView(access);}else f.addView(info("Access status",member.s("status")));}
        if(!hasMember&&hasTech&&accountTeam.hasWorkspace()&&accountTeam.canManageTeam()){f.addView(section("App access"));List<AppDatabase.Row> linkable=db.unlinkedWorkspaceMembers(accountTeam.workspaceId());if(!linkable.isEmpty()){MaterialButton link=outlineButton("Link existing workspace member");link.setOnClickListener(v->showLinkMemberDialog(technicianId));f.addView(link);}MaterialButton invite=outlineButton("Invite this person to workspace");invite.setEnabled(!val(email).isEmpty());invite.setOnClickListener(v->showInviteDialog(val(email),AccountTeamManager.ROLE_TECHNICIAN));f.addView(invite);}
        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle(hasMember||hasTech?"Person profile":"Add field-only person").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Name required");return;}if(!val(email).isEmpty()&&!android.util.Patterns.EMAIL_ADDRESS.matcher(val(email)).matches()){email.setError("Enter a valid email");return;}String n=val(name),fr=val(fieldRole),ph=val(phone),em=val(email),user=hasMember?member.s("user_uuid"):tech.s("user_uuid");boolean fieldEnabled=field.isChecked();Runnable finish=()->{if(fieldEnabled||hasTech)db.saveTechnician(technicianId,AppDatabase.map("name",n,"role",fr,"phone",ph,"email",em,"user_uuid",user,"active",fieldEnabled?"1":"0"));d.dismiss();toast(fieldEnabled?"Person available for field jobs":"Person profile saved");showPeopleTeam();};if(appAccess!=null){String desired=appAccess.isChecked()?"Active":"Inactive";if(!desired.equalsIgnoreCase(member.s("status"))){Runnable change=()->updateWorkspaceMemberAccess(member,member.s("role"),desired,finish);if("Inactive".equals(desired)){new MaterialAlertDialogBuilder(this).setTitle("Disable workspace access?").setMessage(member.s("name")+" will no longer be able to access or synchronize this workspace. Existing jobs, history and the member record are kept, and access can be enabled again later.").setNegativeButton("Keep enabled",null).setPositiveButton("Disable",(a,w)->change.run()).show();}else change.run();return;}}finish.run();}));d.show();
    }

    private void showLinkMemberDialog(long technicianId){
        if(!requireWorkspaceManager("People & Team"))return;
        if(!accountTeam.hasWorkspace())return;List<AppDatabase.Row> members=db.unlinkedWorkspaceMembers(accountTeam.workspaceId());if(members.isEmpty()){toast("No unlinked workspace members available");return;}String[] labels=new String[members.size()];for(int i=0;i<members.size();i++){AppDatabase.Row m=members.get(i);labels[i]=m.s("name")+(m.s("email").isEmpty()?"":" · "+m.s("email"))+" · "+m.s("role");}new MaterialAlertDialogBuilder(this).setTitle("Link to workspace member").setItems(labels,(d,which)->{db.linkTechnicianToMember(technicianId,members.get(which).id());toast("Person linked to workspace access");showPeopleTeam();}).setNegativeButton("Cancel",null).show();
    }

    private void showTechnicians(){
        if(!requireWorkspaceManager("Technician administration"))return;
        setHeader("Technicians","Team members & job assignment");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->showMore());b.addView(back);MaterialButton add=button("+ Add technician");add.setOnClickListener(v->showTechnicianDialog(0));b.addView(add);List<AppDatabase.Row> rows=db.technicians();b.addView(section("Team"));if(rows.isEmpty())b.addView(empty("Add technicians to assign service work consistently."));for(AppDatabase.Row r:rows){String meta=(r.s("role").isEmpty()?"Technician":r.s("role"))+(r.s("phone").isEmpty()?"":" • "+r.s("phone"));MaterialCardView c=rowCard(r.s("name"),meta,r.i("active")==1?"Active":"Inactive");c.setOnClickListener(v->showTechnicianDialog(r.id()));b.addView(c);}
    }

    private void showTechnicianDialog(long id){
        if(!requireWorkspaceManager("Technician administration"))return;
        AppDatabase.Row r=id>0?db.getTechnician(id):new AppDatabase.Row();LinearLayout f=form();EditText name=input("Name *",r.s("name"));EditText role=input("Role",r.s("role"));EditText phone=input("Phone",r.s("phone"));EditText email=input("Email",r.s("email"));Spinner active=spinner(new String[]{"Active","Inactive"});setSpinner(active,id==0||r.i("active")==1?"Active":"Inactive");f.addView(name);f.addView(role);f.addView(phone);f.addView(email);f.addView(label("Status"));f.addView(active);AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle(id>0?"Edit technician":"Add technician").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{if(val(name).isEmpty()){name.setError("Required");return;}db.saveTechnician(id,AppDatabase.map("name",val(name),"role",val(role),"phone",val(phone),"email",val(email),"user_uuid",r.s("user_uuid"),"active","Active".equals(String.valueOf(active.getSelectedItem()))?"1":"0"));d.dismiss();toast("Technician saved");showPeopleTeam();}));d.show();
    }

    private void showAssetDetail(long id){
        AppDatabase.Row a=db.getAsset(id);if(a.id()==0){toast("Asset not found");return;}setHeader(a.s("tag"),"Asset service history");clear();LinearLayout b=body(page());LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);MaterialButton back=outlineButton("← Assets");back.setOnClickListener(v->showAssets());top.addView(back,new LinearLayout.LayoutParams(0,dp(48),1));if(canManageWorkspaceSettings()){top.addView(spacerH());MaterialButton edit=button("Edit");edit.setOnClickListener(v->showAssetDialog(id));top.addView(edit,new LinearLayout.LayoutParams(0,dp(48),1));}b.addView(top);b.addView(section(a.s("name")));b.addView(info("Customer",db.one("SELECT name FROM customers WHERE id=?",new String[]{a.s("customer_id")}).s("name")));b.addView(info("Site",db.one("SELECT name FROM sites WHERE id=?",new String[]{a.s("site_id")}).s("name")));b.addView(info("Category",a.s("category")));b.addView(info("Make / model",a.s("make_model")));b.addView(info("Serial",a.s("serial")));b.addView(info("Location",a.s("location")));b.addView(info("Maintenance interval",a.i("interval_days")>0?a.i("interval_days")+" days":"Not set"));b.addView(info("Next service",a.s("next_service")));
        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);if(canPerformFieldWork()){MaterialButton job=button("+ Service job");job.setOnClickListener(v->showJobDialog(0,id));actions.addView(job,new LinearLayout.LayoutParams(0,dp(50),1));actions.addView(spacerH());}MaterialButton qr=outlineButton("Asset QR");qr.setOnClickListener(v->showAssetQr(a));actions.addView(qr,new LinearLayout.LayoutParams(0,dp(50),1));b.addView(actions);
        List<AppDatabase.Row> jobs=db.jobsForAssetScoped(id,currentJobUserUuid(),canSeeAllJobs());b.addView(section("Service jobs ("+jobs.size()+")"));if(jobs.isEmpty())b.addView(empty("No service jobs recorded for this asset yet."));for(AppDatabase.Row j:jobs){MaterialCardView c=rowCard(j.s("report_no")+" · "+j.s("title"),j.s("job_date")+(j.s("technician").isEmpty()?"":" • "+j.s("technician")),j.s("status"));c.setOnClickListener(v->showJobDetail(j.id()));b.addView(c);}List<AppDatabase.Row> logs=db.maintenanceForAssetScoped(id,currentJobUserUuid(),canSeeAllJobs());b.addView(section("Maintenance log"));if(logs.isEmpty())b.addView(empty("Maintenance completions will appear here."));for(AppDatabase.Row m:logs){String ttl=m.s("report_no").isEmpty()?"Maintenance completed":m.s("report_no")+" · "+m.s("job_title");String meta=m.s("service_date")+(m.s("next_service").isEmpty()?"":" • Next "+m.s("next_service"));b.addView(rowCard(ttl,meta,m.s("notes")));}
    }

    private void migrateDefaultTechnician(){String old=prefs.getString("technician_name","");if(db.count("technicians",null,null)==0&&!old.isEmpty())db.saveTechnician(0,AppDatabase.map("name",old,"role","Technician","phone","","email","","active","1"));}
    private void requestNotificationPermissionIfNeeded(){if(Build.VERSION.SDK_INT>=33&&ContextCompat.checkSelfPermission(this,Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS);}
    private void scheduleMaintenanceReminders(){boolean enabled=prefs.getBoolean("maintenance_notifications",true);if(!enabled){WorkManager.getInstance(this).cancelUniqueWork("fida-maintenance-reminders");return;}PeriodicWorkRequest req=new PeriodicWorkRequest.Builder(MaintenanceReminderWorker.class,24,TimeUnit.HOURS).build();WorkManager.getInstance(this).enqueueUniquePeriodicWork("fida-maintenance-reminders", ExistingPeriodicWorkPolicy.UPDATE,req);}

    private void scanAssetQr(){
        ScanOptions options=new ScanOptions();options.setPrompt("Scan a Fida Field asset QR code");options.setBeepEnabled(false);options.setOrientationLocked(false);options.setDesiredBarcodeFormats(ScanOptions.QR_CODE);qrLauncher.launch(options);
    }

    private void openScannedAsset(String raw){
        String value=raw==null?"":raw.trim();String tag=value;
        if(value.startsWith("fida://asset/"))tag=Uri.decode(value.substring("fida://asset/".length()));
        else if(value.startsWith("FIDAFIELD:"))tag=value.substring("FIDAFIELD:".length()).trim();
        AppDatabase.Row asset=db.getAssetByTag(tag);
        if(asset.id()==0){new MaterialAlertDialogBuilder(this).setTitle("Asset not found").setMessage("No local asset matches QR value:\n"+tag).setPositiveButton("OK",null).show();return;}
        showAssetDetail(asset.id());
    }

    private Bitmap assetQrBitmap(AppDatabase.Row asset)throws Exception{
        String payload="fida://asset/"+Uri.encode(asset.s("tag"));int size=900;BitMatrix matrix=new MultiFormatWriter().encode(payload, BarcodeFormat.QR_CODE,size,size);Bitmap bm=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888);for(int y=0;y<size;y++)for(int x=0;x<size;x++)bm.setPixel(x,y,matrix.get(x,y)?Color.BLACK:Color.WHITE);return bm;
    }

    private void showAssetQr(AppDatabase.Row asset){
        try{Bitmap bm=assetQrBitmap(asset);LinearLayout wrap=form();TextView h=heading(asset.s("tag"));h.setGravity(Gravity.CENTER);wrap.addView(h);wrap.addView(paragraph(asset.s("name")+"\nScan with Fida Field to open this asset."));ImageView image=new ImageView(this);image.setImageBitmap(bm);image.setAdjustViewBounds(true);wrap.addView(image,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(300)));new MaterialAlertDialogBuilder(this).setTitle("Asset QR").setView(scrollForm(wrap)).setNegativeButton("Close",(d,w)->bm.recycle()).setPositiveButton("Share",(d,w)->{try{shareAssetQr(asset,bm);}catch(Exception e){error("Could not share QR",e);}finally{bm.recycle();}}).show();}catch(Exception e){error("Could not create QR",e);}
    }

    private void shareAssetQr(AppDatabase.Row asset,Bitmap bm)throws Exception{
        File dir=new File(getFilesDir(),"qr");if(!dir.exists()&&!dir.mkdirs())throw new Exception("Could not create QR folder");File file=new File(dir,"FidaField-"+asset.s("tag").replaceAll("[^A-Za-z0-9._-]","_")+".png");try(FileOutputStream out=new FileOutputStream(file)){bm.compress(Bitmap.CompressFormat.PNG,100,out);}Uri uri=FileProvider.getUriForFile(this,getPackageName()+".files",file);Intent share=new Intent(Intent.ACTION_SEND);share.setType("image/png");share.putExtra(Intent.EXTRA_STREAM,uri);share.putExtra(Intent.EXTRA_TEXT,asset.s("tag")+" · "+asset.s("name"));share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(share,"Share asset QR"));
    }

    private void exportFullBackup(Uri target)throws Exception{
        JSONObject root=db.exportJson();JSONObject settings=new JSONObject();String[] keys={"company_name","technician_name","company_phone","company_email","company_address","report_prefix","theme","maintenance_reminder_days",BrandingManager.KEY_PRIMARY,BrandingManager.KEY_ACCENT,BrandingManager.KEY_HIGHLIGHT};for(String k:keys)settings.put(k,prefs.getString(k,""));settings.put("maintenance_notifications",prefs.getBoolean("maintenance_notifications",true));settings.put(BrandingManager.KEY_ENABLED,prefs.getBoolean(BrandingManager.KEY_ENABLED,false));root.put("_settings",settings);root.put("_format","FidaFieldBackup");root.put("_version",3);
        OutputStream raw=getContentResolver().openOutputStream(target);if(raw==null)throw new Exception("Unable to create backup file");try(ZipOutputStream zip=new ZipOutputStream(raw)){
            File brandLogo=branding.logoFile(this);if(brandLogo.isFile()){String entry="media/branding/custom_logo.png";try(InputStream in=new FileInputStream(brandLogo)){writeZipEntry(zip,entry,in);root.put("_branding_logo","backup://"+entry);}}
            JSONArray photos=root.optJSONArray("job_photos");if(photos!=null)for(int i=0;i<photos.length();i++){JSONObject o=photos.getJSONObject(i);String source=o.optString("uri");if(source.isEmpty())continue;String entry="media/photos/photo_"+o.optString("id")+".jpg";try(InputStream in=getContentResolver().openInputStream(Uri.parse(source))){if(in!=null){writeZipEntry(zip,entry,in);o.put("uri","backup://"+entry);}}catch(Exception ignored){}}
            JSONArray jobs=root.optJSONArray("jobs");if(jobs!=null)for(int i=0;i<jobs.length();i++){JSONObject o=jobs.getJSONObject(i);String source=o.optString("signature_path");if(source.isEmpty())continue;File f=new File(source);if(!f.isFile())continue;String entry="media/signatures/job_"+o.optString("id")+".png";try(InputStream in=new FileInputStream(f)){writeZipEntry(zip,entry,in);o.put("signature_path","backup://"+entry);}}
            zip.putNextEntry(new ZipEntry("manifest.json"));zip.write(root.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8));zip.closeEntry();
        }
    }

    private void writeZipEntry(ZipOutputStream zip,String name,InputStream in)throws Exception{zip.putNextEntry(new ZipEntry(name));byte[] buf=new byte[8192];int n;while((n=in.read(buf))>0)zip.write(buf,0,n);zip.closeEntry();}

    private void restoreBackup(Uri source)throws Exception{
        try(InputStream probe=getContentResolver().openInputStream(source)){if(probe==null)throw new Exception("Unable to read backup");java.io.PushbackInputStream pb=new java.io.PushbackInputStream(probe,4);byte[] head=new byte[4];int n=pb.read(head);if(n>0)pb.unread(head,0,n);if(n>=2&&head[0]=='P'&&head[1]=='K')restoreZip(pb);else{byte[] data=readAll(pb);db.importJson(new JSONObject(new String(data,java.nio.charset.StandardCharsets.UTF_8)));}}
    }

    private void restoreZip(InputStream raw)throws Exception{
        File mediaRoot=new File(getFilesDir(),"restored_media");if(!mediaRoot.exists()&&!mediaRoot.mkdirs())throw new Exception("Could not create restore folder");JSONObject manifest=null;try(ZipInputStream zip=new ZipInputStream(raw)){ZipEntry e;while((e=zip.getNextEntry())!=null){String name=e.getName();if("manifest.json".equals(name)){manifest=new JSONObject(new String(readAll(zip),java.nio.charset.StandardCharsets.UTF_8));}else if(name.startsWith("media/")&&!e.isDirectory()){File out=safeBackupFile(mediaRoot,name.substring("media/".length()));File parent=out.getParentFile();if(parent!=null&&!parent.exists()&&!parent.mkdirs())throw new Exception("Could not create media folder");try(FileOutputStream fos=new FileOutputStream(out)){byte[] buf=new byte[8192];int n;while((n=zip.read(buf))>0)fos.write(buf,0,n);}}zip.closeEntry();}}
        if(manifest==null)throw new Exception("Backup manifest is missing");JSONArray photos=manifest.optJSONArray("job_photos");if(photos!=null)for(int i=0;i<photos.length();i++){JSONObject o=photos.getJSONObject(i);String v=o.optString("uri");if(v.startsWith("backup://media/")){File f=safeBackupFile(mediaRoot,v.substring("backup://media/".length()));o.put("uri",Uri.fromFile(f).toString());}}
        JSONArray jobs=manifest.optJSONArray("jobs");if(jobs!=null)for(int i=0;i<jobs.length();i++){JSONObject o=jobs.getJSONObject(i);String v=o.optString("signature_path");if(v.startsWith("backup://media/")){File f=safeBackupFile(mediaRoot,v.substring("backup://media/".length()));o.put("signature_path",f.getAbsolutePath());}}
        db.importJson(manifest);JSONObject settings=manifest.optJSONObject("_settings");if(settings!=null){SharedPreferences.Editor ed=prefs.edit();java.util.Iterator<String> it=settings.keys();while(it.hasNext()){String k=it.next();if("maintenance_notifications".equals(k)||BrandingManager.KEY_ENABLED.equals(k))ed.putBoolean(k,settings.optBoolean(k,false));else ed.putString(k,settings.optString(k,""));}ed.apply();}
        String brandRef=manifest.optString("_branding_logo");if(brandRef.startsWith("backup://media/")){File source=safeBackupFile(mediaRoot,brandRef.substring("backup://media/".length()));if(source.isFile()){File target=branding.logoFile(this);File parent=target.getParentFile();if(parent!=null&&!parent.exists())parent.mkdirs();try(InputStream in=new FileInputStream(source);FileOutputStream out=new FileOutputStream(target)){byte[] buf=new byte[8192];int n;while((n=in.read(buf))>0)out.write(buf,0,n);}}}
        refreshEntitlementsAndBranding();
    }

    private File safeBackupFile(File root,String relative)throws Exception{File f=new File(root,relative);String rootPath=root.getCanonicalPath()+File.separator;String filePath=f.getCanonicalPath();if(!filePath.startsWith(rootPath))throw new Exception("Unsafe backup path");return f;}

    private void generateAndShare(long jobId){
        try{
            File f=ProfessionalPdfReport.generate(this,db,jobId,prefs);AppDatabase.Row j=db.getJob(jobId);String email=j.s("customer_email").trim();
            if("Completed".equalsIgnoreCase(j.s("status"))&&!email.isEmpty())showCompletedReportDelivery(f,j);else shareReportFile(f,j,"");
        }catch(Exception e){error("PDF generation failed",e);}
    }

    private void showCompletedReportDelivery(File file,AppDatabase.Row job){
        String email=job.s("customer_email").trim();String customer=job.s("customer_name").isEmpty()?"customer":job.s("customer_name");
        new MaterialAlertDialogBuilder(this).setTitle("Final report ready").setMessage("The completed service report is ready. Email it to "+customer+" at "+email+" or share it with another app.")
                .setNegativeButton("Cancel",null).setNeutralButton("Share…",(d,w)->shareReportFile(file,job,""))
                .setPositiveButton("Email customer",(d,w)->shareReportFile(file,job,email)).show();
    }

    private void shareReportFile(File file,AppDatabase.Row job,String email){
        Uri uri=FileProvider.getUriForFile(this,getPackageName()+".files",file);
        Intent share=new Intent(Intent.ACTION_SEND);
        share.setType("application/pdf");
        share.putExtra(Intent.EXTRA_STREAM,uri);
        if(email!=null&&!email.trim().isEmpty())share.putExtra(Intent.EXTRA_EMAIL,new String[]{email.trim()});
        String company=prefs.getString("company_name","Fidalix Limited");
        String subject="Service report "+job.s("report_no")+" — "+company;
        share.putExtra(Intent.EXTRA_SUBJECT,subject);
        String contact=job.s("customer_contact").trim();
        String greeting=contact.isEmpty()?"Hello,":"Hello "+contact+",";
        share.putExtra(Intent.EXTRA_TEXT,greeting+"\n\nPlease find attached the completed service report "+job.s("report_no")+" for "+job.s("title")+".\n\nKind regards,\n"+company);
        share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivity(Intent.createChooser(share,email==null||email.trim().isEmpty()?"Share service report":"Email service report"));
    }

    private void shareCsv(String type){
        try{File dir=new File(getFilesDir(),"reports");if(!dir.exists())dir.mkdirs();File f=new File(dir,"FidaField-"+type+"-"+db.today()+".csv");StringBuilder out=new StringBuilder();if("assets".equals(type)){out.append("Tag,Asset,Category,Make/Model,Serial,Customer,Site,Location,Interval Days,Next Service\n");for(AppDatabase.Row r:db.assets(0,0))out.append(csv(r.s("tag"))).append(',').append(csv(r.s("name"))).append(',').append(csv(r.s("category"))).append(',').append(csv(r.s("make_model"))).append(',').append(csv(r.s("serial"))).append(',').append(csv(r.s("customer_name"))).append(',').append(csv(r.s("site_name"))).append(',').append(csv(r.s("location"))).append(',').append(csv(r.s("interval_days"))).append(',').append(csv(r.s("next_service"))).append('\n');}else{out.append("Report No,Date,Status,Priority,Customer,Site,Asset,Title,Technician,Problem,Diagnosis,Work Done,Parts,Next Service\n");for(AppDatabase.Row r:db.jobsFilteredScoped("","All","All","All","","",currentJobUserUuid(),canSeeAllJobs()))out.append(csv(r.s("report_no"))).append(',').append(csv(r.s("job_date"))).append(',').append(csv(r.s("status"))).append(',').append(csv(r.s("priority"))).append(',').append(csv(r.s("customer_name"))).append(',').append(csv(r.s("site_name"))).append(',').append(csv(r.s("asset_name"))).append(',').append(csv(r.s("title"))).append(',').append(csv(r.s("technician"))).append(',').append(csv(r.s("problem"))).append(',').append(csv(r.s("diagnosis"))).append(',').append(csv(r.s("work_done"))).append(',').append(csv(r.s("parts"))).append(',').append(csv(r.s("next_service"))).append('\n');}try(FileOutputStream fos=new FileOutputStream(f)){fos.write(out.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));}Uri uri=FileProvider.getUriForFile(this,getPackageName()+".files",f);Intent share=new Intent(Intent.ACTION_SEND);share.setType("text/csv");share.putExtra(Intent.EXTRA_STREAM,uri);share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(share,"Share "+type+" CSV"));}catch(Exception e){error("CSV export failed",e);}
    }
    private String csv(String v){String x=v==null?"":v;if(x.contains(",")||x.contains("\n")||x.contains("\r")||x.contains("\""))return "\""+x.replace("\"","\"\"")+"\"";return x;}

    private String[] technicianFilterValues(){ArrayList<String> v=new ArrayList<>();v.add("All");v.add("Unassigned");for(AppDatabase.Row r:db.technicians())if(!v.contains(r.s("name")))v.add(r.s("name"));return v.toArray(new String[0]);}
    private String[] dateRange(String preset){String today=db.today();if("All dates".equals(preset))return new String[]{"",""};Calendar c=Calendar.getInstance();SimpleDateFormat f=new SimpleDateFormat("yyyy-MM-dd",Locale.US);if("Today".equals(preset))return new String[]{today,today};if("Last 7 days".equals(preset)){c.add(Calendar.DAY_OF_YEAR,-6);return new String[]{f.format(c.getTime()),today};}if("Last 30 days".equals(preset)){c.add(Calendar.DAY_OF_YEAR,-29);return new String[]{f.format(c.getTime()),today};}if("This year".equals(preset)){return new String[]{String.format(Locale.US,"%04d-01-01",c.get(Calendar.YEAR)),today};}return new String[]{"",""};}

    private List<Choice> customerChoices(boolean empty){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— None —"));for(AppDatabase.Row r:db.customers())out.add(new Choice(r.id(),r.s("name")));return out;}
    private List<Choice> siteChoices(boolean empty){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— None —"));for(AppDatabase.Row r:db.sites(0))out.add(new Choice(r.id(),r.s("customer_name")+" / "+r.s("name")));return out;}
    private List<Choice> assetChoices(boolean empty){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— None —"));for(AppDatabase.Row r:db.assets(0,0))out.add(new Choice(r.id(),r.s("tag")+" / "+r.s("name")));return out;}
    private List<Choice> technicianChoices(boolean empty,String current){ArrayList<Choice> out=new ArrayList<>();if(empty)out.add(new Choice(0,"— Unassigned —"));boolean found=current==null||current.isEmpty();for(AppDatabase.Row r:db.activeTechnicians()){out.add(new Choice(r.id(),r.s("name")));if(r.s("name").equals(current))found=true;}if(!found)out.add(new Choice(-1,current));return out;}
    private String choiceLabel(Spinner s){Object o=s.getSelectedItem();return o instanceof Choice&&((Choice)o).id!=0?((Choice)o).label:"";}
    private void setChoiceByLabel(Spinner s,String label){if(label==null)return;for(int i=0;i<s.getCount();i++){Object o=s.getItemAtPosition(i);if(o instanceof Choice&&((Choice)o).label.equals(label)){s.setSelection(i);return;}}}
    private Spinner choiceSpinner(List<Choice> list){Spinner s=new Spinner(this);ArrayAdapter<Choice>a=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,list);a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);s.setAdapter(a);styleSpinner(s);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(4),0,dp(7));s.setLayoutParams(p);return s;}
    private void setChoice(Spinner s,long id){for(int i=0;i<s.getCount();i++){Object o=s.getItemAtPosition(i);if(o instanceof Choice&&((Choice)o).id==id){s.setSelection(i);return;}}}

    private void refreshCurrent(){navigate(currentMenu);}
    private long parse(String s){try{return Long.parseLong(s==null||s.isEmpty()?"0":s);}catch(Exception e){return 0;}}
    private void pickDate(EditText field){Calendar c=Calendar.getInstance();String v=val(field);try{java.util.Date d=new SimpleDateFormat("yyyy-MM-dd",Locale.US).parse(v);if(d!=null)c.setTime(d);}catch(Exception ignored){}new DatePickerDialog(this,(view,y,m,d)->field.setText(String.format(Locale.US,"%04d-%02d-%02d",y,m+1,d)),c.get(Calendar.YEAR),c.get(Calendar.MONTH),c.get(Calendar.DAY_OF_MONTH)).show();}

    private LinearLayout form(){LinearLayout f=new LinearLayout(this);f.setOrientation(LinearLayout.VERTICAL);f.setPadding(dp(4),dp(4),dp(4),dp(10));return f;}
    private ScrollView scrollForm(View f){ScrollView s=new ScrollView(this);s.setFillViewport(true);s.setPadding(dp(4),0,dp(4),0);s.addView(f);return s;}
    private EditText input(String hint,String value){EditText e=new EditText(this);e.setHint(hint);e.setText(value==null?"":value);e.setTextSize(15);e.setTextColor(textColor());e.setHintTextColor(mutedColor());e.setSingleLine(true);e.setPadding(dp(16),dp(11),dp(16),dp(11));e.setBackground(rounded(surface(),borderColor(),dp(1),dp(16)));e.setSelectAllOnFocus(false);e.setOnFocusChangeListener((v,focused)->e.setBackground(rounded(surface(),focused?ACCENT:borderColor(),focused?dp(2):dp(1),dp(16))));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(58));p.setMargins(0,dp(6),0,dp(6));e.setLayoutParams(p);return e;}
    private EditText multi(String hint,String value){EditText e=input(hint,value);e.setSingleLine(false);e.setGravity(Gravity.TOP);e.setMinLines(3);e.setMaxLines(6);e.getLayoutParams().height=dp(104);return e;}
    private String val(EditText e){return e.getText()==null?"":e.getText().toString().trim();}
    private Spinner spinner(String[] values){Spinner s=new Spinner(this);ArrayAdapter<String>a=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,values);a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);s.setAdapter(a);styleSpinner(s);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(4),0,dp(7));s.setLayoutParams(p);return s;}
    private void styleSpinner(Spinner s){s.setPadding(dp(12),dp(4),dp(10),dp(4));s.setBackground(rounded(surface(),borderColor(),dp(1),dp(13)));try{s.setPopupBackgroundDrawable(rounded(surface(),borderColor(),dp(1),dp(10)));}catch(Exception ignored){}}
    private void setSpinner(Spinner s,String value){for(int i=0;i<s.getCount();i++)if(String.valueOf(s.getItemAtPosition(i)).equals(value)){s.setSelection(i);break;}}

    private MaterialButton button(String text){MaterialButton b=new MaterialButton(this);b.setText(text);b.setTextSize(14);b.setAllCaps(false);b.setLetterSpacing(0.01f);b.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));b.setCornerRadius(dp(16));b.setInsetTop(0);b.setInsetBottom(0);b.setBackgroundTintList(ColorStateList.valueOf(ACCENT));b.setTextColor(onColor(ACCENT));b.setRippleColor(ColorStateList.valueOf(0x33FFFFFF));b.setElevation(dp(1));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(6),0,dp(6));b.setLayoutParams(p);return b;}
    private MaterialButton outlineButton(String text){MaterialButton b=button(text);b.setBackgroundTintList(ColorStateList.valueOf(surface()));b.setTextColor(brandTextColor());b.setStrokeColor(ColorStateList.valueOf(isNight()?0xFF6B716A:BRAND));b.setStrokeWidth(dp(1));b.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x14464B45));return b;}
    private TextView heading(String s){TextView t=new TextView(this);t.setText(s);t.setTextSize(25);t.setTextColor(textColor());t.setTypeface(android.graphics.Typeface.create("sans-serif",android.graphics.Typeface.BOLD));t.setPadding(0,dp(7),0,dp(4));return t;}
    private TextView paragraph(String s){TextView t=new TextView(this);t.setText(s);t.setTextSize(14);t.setTextColor(mutedColor());t.setLineSpacing(0,1.18f);t.setPadding(0,0,0,dp(9));return t;}
    private TextView section(String s){TextView t=new TextView(this);t.setText(s);t.setTextSize(15);t.setLetterSpacing(0.01f);t.setTextColor(textColor());t.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));t.setPadding(0,dp(26),0,dp(11));GradientDrawable mark=rounded(ACCENT,0,0,dp(3));mark.setBounds(0,0,dp(5),dp(19));t.setCompoundDrawables(mark,null,null,null);t.setCompoundDrawablePadding(dp(10));return t;}
    private TextView label(String s){TextView t=new TextView(this);t.setText(s.toUpperCase(Locale.US));t.setLetterSpacing(0.06f);t.setTextSize(10);t.setTextColor(mutedColor());t.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));t.setPadding(dp(2),dp(10),0,dp(3));return t;}
    private View spacerH(){View v=new View(this);v.setLayoutParams(new LinearLayout.LayoutParams(dp(10),1));return v;}
    private TextView empty(String s){TextView t=paragraph(s);t.setGravity(Gravity.CENTER);t.setPadding(dp(16),dp(22),dp(16),dp(22));t.setBackground(rounded(softSurface(),borderColor(),dp(1),dp(16)));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(0,dp(5),0,dp(5));t.setLayoutParams(p);return t;}

    private MaterialCardView heroCard(String headline,String copy){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(paleAccent());c.setRadius(dp(22));c.setStrokeColor(paleAccentBorder());c.setStrokeWidth(dp(1));c.setCardElevation(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(18),dp(15),dp(18),dp(16));LinearLayout kicker=new LinearLayout(this);kicker.setGravity(Gravity.CENTER_VERTICAL);View dot=new View(this);dot.setBackground(rounded(ACCENT,0,0,dp(6)));kicker.addView(dot,new LinearLayout.LayoutParams(dp(8),dp(8)));TextView eyebrow=new TextView(this);eyebrow.setText("FIDA FIELD  •  OPERATIONS");eyebrow.setTextSize(9);eyebrow.setLetterSpacing(0.12f);eyebrow.setTextColor(brandTextColor());eyebrow.setPadding(dp(8),0,0,0);eyebrow.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));kicker.addView(eyebrow);TextView h=heading(headline);h.setTextSize(22);h.setPadding(0,dp(7),0,dp(3));TextView p=paragraph(copy);p.setTextSize(13);p.setPadding(0,0,0,0);l.addView(kicker);l.addView(h);l.addView(p);c.addView(l);LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,0,0,dp(8));c.setLayoutParams(cp);return c;}
    private MaterialCardView brandPanel(){
        MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(20));c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));c.setCardElevation(0);LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);l.setGravity(Gravity.CENTER_VERTICAL);l.setPadding(dp(16),dp(13),dp(16),dp(13));
        ImageView logo=new ImageView(this);Bitmap custom=branding==null?null:branding.loadCustomLogo(this);if(custom!=null)logo.setImageBitmap(custom);else logo.setImageResource(R.drawable.fidalix_logo);logo.setAdjustViewBounds(true);logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);l.addView(logo,new LinearLayout.LayoutParams(dp(126),dp(44)));
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.setPadding(dp(13),0,0,0);TextView a=new TextView(this);a.setText(branding!=null&&branding.isActive()?prefs.getString("company_name","Company branding"):"Fida Field");a.setTextSize(15);a.setTextColor(textColor());a.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));TextView b=new TextView(this);b.setText(branding!=null&&branding.isActive()?"Custom Pro branding · Powered by Fida Field":"Service & Maintenance");b.setTextSize(11);b.setTextColor(mutedColor());copy.addView(a);copy.addView(b);l.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));c.addView(l);LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,0,0,dp(4));c.setLayoutParams(cp);return c;
    }

    private MaterialCardView dashboardStat(String label,long value,View.OnClickListener action){
        MaterialCardView c=stat(label,value);
        if(value>0&&action!=null){
            c.setClickable(true);c.setFocusable(true);c.setAlpha(1f);c.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x12F99D1C));c.setOnClickListener(action);
        }else{
            c.setClickable(false);c.setFocusable(false);c.setCardElevation(0);c.setCardBackgroundColor(softSurface());c.setStrokeColor(isNight()?0xFF343934:0xFFE7E9E6);c.setAlpha(isNight()?0.74f:0.72f);
        }
        return c;
    }
    private MaterialCardView stat(String label,long value){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(22));c.setCardElevation(dp(1));c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setGravity(Gravity.CENTER_VERTICAL);l.setPadding(dp(16),dp(14),dp(16),dp(13));LinearLayout top=new LinearLayout(this);top.setGravity(Gravity.CENTER_VERTICAL);View dot=new View(this);dot.setBackground(rounded(ACCENT,0,0,dp(6)));top.addView(dot,new LinearLayout.LayoutParams(dp(9),dp(9)));TextView lab=new TextView(this);lab.setText(label);lab.setTextSize(11);lab.setTextColor(mutedColor());lab.setPadding(dp(7),0,0,0);top.addView(lab);TextView n=new TextView(this);n.setText(String.valueOf(value));n.setTextSize(29);n.setTextColor(textColor());n.setTypeface(android.graphics.Typeface.create("sans-serif",android.graphics.Typeface.BOLD));n.setPadding(0,dp(6),0,0);l.addView(top);l.addView(n);c.addView(l);return c;}
    private MaterialCardView rowCard(String a,String b,String badge){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(20));c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));c.setCardElevation(dp(1));c.setClickable(true);c.setFocusable(true);c.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x12F99D1C));LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,dp(6),0,dp(6));c.setLayoutParams(cp);LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(16),dp(14),dp(14),dp(14));View rail=new View(this);rail.setBackground(rounded(paleAccentBorder(),0,0,dp(2)));LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(dp(4),dp(38));rp.setMargins(0,0,dp(12),0);row.addView(rail,rp);LinearLayout txt=new LinearLayout(this);txt.setOrientation(LinearLayout.VERTICAL);TextView t1=new TextView(this);t1.setText(a);t1.setTextSize(15);t1.setTextColor(textColor());t1.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));TextView t2=new TextView(this);t2.setText(b);t2.setTextSize(12);t2.setTextColor(mutedColor());t2.setPadding(0,dp(4),0,0);txt.addView(t1);txt.addView(t2);row.addView(txt,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));if(badge!=null&&!badge.isEmpty()){TextView x=badgeView(badge);row.addView(x);}c.addView(row);return c;}
    private TextView badgeView(String text){String l=text.toLowerCase(Locale.US);int fg=brandTextColor(),bg=paleAccent(),stroke=paleAccentBorder();if(l.contains("completed")){fg=isNight()?0xFF86D8AD:0xFF287451;bg=isNight()?0xFF20382C:0xFFE9F6EF;stroke=isNight()?0xFF315A42:0xFFCBE8D8;}else if(l.contains("cancel")||l.contains("overdue")||l.contains("urgent")){fg=isNight()?0xFFFFA8A4:0xFFA63D38;bg=isNight()?0xFF422725:0xFFFFEEEE;stroke=isNight()?0xFF69403C:0xFFF3CAC7;}else if(l.contains("progress")||l.contains("due")||l.contains("pro")||l.contains("pdf")){fg=ACCENT;bg=paleAccent();stroke=paleAccentBorder();}TextView x=new TextView(this);x.setText(text);x.setTextSize(10);x.setTextColor(fg);x.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));x.setGravity(Gravity.CENTER);x.setPadding(dp(9),dp(5),dp(9),dp(5));x.setBackground(rounded(bg,stroke,dp(1),dp(14)));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(dp(10),0,0,0);x.setLayoutParams(p);return x;}
    private MaterialCardView menuCard(String a,String b,View.OnClickListener l){MaterialCardView c=rowCard(a,b,"›");c.setOnClickListener(l);return c;}
    private View info(String label,String value){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(2),dp(5),dp(2),dp(8));TextView a=new TextView(this);a.setText(label.toUpperCase(Locale.US));a.setLetterSpacing(0.06f);a.setTextSize(10);a.setTextColor(mutedColor());a.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));TextView v=new TextView(this);v.setText(value==null||value.isEmpty()?"—":value);v.setTextSize(14);v.setTextColor(textColor());v.setPadding(0,dp(3),0,0);l.addView(a);l.addView(v);return l;}
    private GradientDrawable rounded(int fill,int stroke,int strokeWidth,int radius){GradientDrawable g=new GradientDrawable();g.setColor(fill);g.setCornerRadius(radius);if(strokeWidth>0)g.setStroke(strokeWidth,stroke);return g;}
    private void addIf(LinearLayout b,String label,String val){if(val!=null&&!val.isEmpty()){b.addView(section(label));b.addView(paragraph(val));}}
    private TextWatcher watcher(Runnable r){return new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int c,int a){}public void onTextChanged(CharSequence s,int st,int before,int count){r.run();}public void afterTextChanged(Editable e){}};}
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private void toast(String s){Toast.makeText(this,s,Toast.LENGTH_SHORT).show();}
    private void error(String title,Exception e){new MaterialAlertDialogBuilder(this).setTitle(title).setMessage(e.getMessage()==null?e.toString():e.getMessage()).setPositiveButton("OK",null).show();}
}
