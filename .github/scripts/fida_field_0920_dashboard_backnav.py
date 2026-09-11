from pathlib import Path


def require_replace(text, old, new, label):
    if new in text:
        return text
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = p.read_text()

# Android system/device back gesture should navigate inside Fida Field first.
s = require_replace(
    s,
    'import androidx.activity.result.ActivityResultLauncher;\n',
    'import androidx.activity.OnBackPressedCallback;\nimport androidx.activity.result.ActivityResultLauncher;\n',
    'OnBackPressedCallback import')

s = require_replace(
    s,
    '    private int currentMenu=MENU_DASH;\n',
    '    private int currentMenu=MENU_DASH;\n    private boolean mainTabScreen=true;\n',
    'main tab state')

s = require_replace(
    s,
    '        buildChrome();\n        if(captureWorkspaceInviteIntent(getIntent())||hasPendingWorkspaceInvite())showAccountWorkspace();else showDashboard();\n',
    '        buildChrome();\n        installAppBackNavigation();\n        if(captureWorkspaceInviteIntent(getIntent())||hasPendingWorkspaceInvite())showAccountWorkspace();else showDashboard();\n',
    'install app back navigation')

back_anchor = '    private void applyThemeMode(String mode){\n'
back_method = '''    private void installAppBackNavigation(){
        getOnBackPressedDispatcher().addCallback(this,new OnBackPressedCallback(true){
            @Override public void handleOnBackPressed(){
                if(!mainTabScreen){navigate(currentMenu);return;}
                if(currentMenu!=MENU_DASH){showDashboard();return;}
                finish();
            }
        });
    }

'''
if 'private void installAppBackNavigation()' not in s:
    if back_anchor not in s:
        raise AssertionError('missing back navigation method anchor')
    s = s.replace(back_anchor, back_method + back_anchor, 1)

# Every full-screen page is treated as a detail page by default. The five bottom
# navigation destinations explicitly mark themselves as top-level screens.
s = require_replace(
    s,
    '    private void setHeader(String a,String b){title.setText(a);subtitle.setText(b);}\n',
    '    private void setHeader(String a,String b){mainTabScreen=false;title.setText(a);subtitle.setText(b);}\n',
    'setHeader navigation state')

for old, new, label in [
    ('currentMenu=MENU_DASH;bottom.getMenu().findItem(MENU_DASH).setChecked(true);setHeader("Fida Field","Service & Maintenance");clear();',
     'currentMenu=MENU_DASH;bottom.getMenu().findItem(MENU_DASH).setChecked(true);setHeader("Fida Field","Service & Maintenance");mainTabScreen=true;clear();', 'dashboard top level'),
    ('currentMenu=MENU_JOBS;bottom.getMenu().findItem(MENU_JOBS).setChecked(true);setHeader("Jobs","Search, filter & service history");clear();',
     'currentMenu=MENU_JOBS;bottom.getMenu().findItem(MENU_JOBS).setChecked(true);setHeader("Jobs","Search, filter & service history");mainTabScreen=true;clear();', 'jobs top level'),
    ('currentMenu=MENU_CUSTOMERS;bottom.getMenu().findItem(MENU_CUSTOMERS).setChecked(true);setHeader("Customers","Clients, sites & service history");clear();',
     'currentMenu=MENU_CUSTOMERS;bottom.getMenu().findItem(MENU_CUSTOMERS).setChecked(true);setHeader("Customers","Clients, sites & service history");mainTabScreen=true;clear();', 'customers top level'),
    ('currentMenu=MENU_ASSETS;bottom.getMenu().findItem(MENU_ASSETS).setChecked(true);setHeader("Assets","Equipment & maintenance");clear();',
     'currentMenu=MENU_ASSETS;bottom.getMenu().findItem(MENU_ASSETS).setChecked(true);setHeader("Assets","Equipment & maintenance");mainTabScreen=true;clear();', 'assets top level'),
    ('currentMenu=MENU_MORE;bottom.getMenu().findItem(MENU_MORE).setChecked(true);setHeader("More","Reports, maintenance & settings");clear();',
     'currentMenu=MENU_MORE;bottom.getMenu().findItem(MENU_MORE).setChecked(true);setHeader("More","Reports, maintenance & settings");mainTabScreen=true;clear();', 'more top level'),
]:
    s = require_replace(s, old, new, label)

# Make non-zero home summary cards clearly interactive, while zero-value cards
# stay inert.
stat_anchor = '    private MaterialCardView stat(String label,long value){'
stat_helper = '''    private MaterialCardView dashboardStat(String label,long value,View.OnClickListener action){
        MaterialCardView c=stat(label,value);
        if(value>0&&action!=null){c.setClickable(true);c.setFocusable(true);c.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x12F99D1C));c.setOnClickListener(action);}
        else{c.setClickable(false);c.setFocusable(false);}
        return c;
    }
'''
if 'private MaterialCardView dashboardStat(' not in s:
    if stat_anchor not in s:
        raise AssertionError('missing stat helper anchor')
    s = s.replace(stat_anchor, stat_helper + stat_anchor, 1)

old_stats = '        LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(stat("Open jobs",db.visibleOpenJobCount(currentJobUserUuid(),canSeeAllJobs())),new LinearLayout.LayoutParams(0,dp(108),1));stats.addView(spacerH());stats.addView(stat("Due ≤30d",db.dueAssets(30).size()),new LinearLayout.LayoutParams(0,dp(108),1));b.addView(stats);\n'
new_stats = '        long openJobs=db.visibleOpenJobCount(currentJobUserUuid(),canSeeAllJobs());long due30=db.dueAssets(30).size();LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(dashboardStat("Open jobs",openJobs,v->showJobs()),new LinearLayout.LayoutParams(0,dp(108),1));stats.addView(spacerH());stats.addView(dashboardStat("Due ≤30d",due30,v->showMaintenance(30)),new LinearLayout.LayoutParams(0,dp(108),1));b.addView(stats);\n'
s = require_replace(s, old_stats, new_stats, 'dashboard primary cards')

old_stats2 = '        LinearLayout stats2=new LinearLayout(this);stats2.setOrientation(LinearLayout.HORIZONTAL);stats2.setPadding(0,dp(8),0,0);stats2.addView(stat("Customers",db.count("customers",null,null)),new LinearLayout.LayoutParams(0,dp(108),1));stats2.addView(spacerH());stats2.addView(stat("Assets",db.count("assets",null,null)),new LinearLayout.LayoutParams(0,dp(108),1));b.addView(stats2);\n'
new_stats2 = '        long customerCount=db.count("customers",null,null),assetCount=db.count("assets",null,null);LinearLayout stats2=new LinearLayout(this);stats2.setOrientation(LinearLayout.HORIZONTAL);stats2.setPadding(0,dp(8),0,0);stats2.addView(dashboardStat("Customers",customerCount,v->showCustomers()),new LinearLayout.LayoutParams(0,dp(108),1));stats2.addView(spacerH());stats2.addView(dashboardStat("Assets",assetCount,v->showAssets()),new LinearLayout.LayoutParams(0,dp(108),1));b.addView(stats2);\n'
s = require_replace(s, old_stats2, new_stats2, 'dashboard customer and asset cards')

# The Due <=30d card opens a matching 30-day maintenance list; the More menu
# keeps the existing 90-day planner.
maintenance_start = '    private void showMaintenance(){\n'
maintenance_end = '    private void showMaintenanceAction(AppDatabase.Row asset){\n'
if 'private void showMaintenance(int days)' not in s:
    a = s.find(maintenance_start)
    b = s.find(maintenance_end, a)
    if a < 0 or b < 0:
        raise AssertionError('missing maintenance method anchors')
    replacement = '''    private void showMaintenance(){showMaintenance(90);}
    private void showMaintenance(int days){
        int window=Math.max(1,days);setHeader("Maintenance","Upcoming & overdue service");clear();LinearLayout b=body(page());MaterialButton back=outlineButton("← Back");back.setOnClickListener(v->navigate(currentMenu));b.addView(back);List<AppDatabase.Row> rows=db.dueAssets(window);b.addView(section("Due within "+window+" days"));if(rows.isEmpty())b.addView(empty("No maintenance due in the next "+window+" days."));else for(AppDatabase.Row r:rows){String state=r.s("next_service").compareTo(db.today())<0?"OVERDUE":"Due "+r.s("next_service");MaterialCardView card=rowCard(r.s("name"),r.s("customer_name")+(r.s("site_name").isEmpty()?"":" • "+r.s("site_name")),state);card.setOnClickListener(v->showMaintenanceAction(r));b.addView(card);}
    }

'''
    s = s[:a] + replacement + s[b:]

s = s.replace('Fida Field 0.9.19 Test\\nInvitation history cleanup, technician identity reconciliation and workspace role security by Fidalix.', 'Fida Field 0.9.20 Test\\nClickable dashboard summaries, Android back navigation, invitation cleanup and cloud sync fixes by Fidalix.')
p.write_text(s)

# Version bump.
p = Path('fida-field/app/build.gradle')
s = p.read_text()
if "versionName '0.9.20-test'" not in s:
    if 'versionCode 22' not in s or "versionName '0.9.19-test'" not in s:
        raise AssertionError('unexpected version before 0.9.20 bump')
    s = s.replace('versionCode 22','versionCode 23',1).replace("versionName '0.9.19-test'","versionName '0.9.20-test'",1)
p.write_text(s)

print('Fida Field 0.9.20 dashboard and back navigation patch applied')
