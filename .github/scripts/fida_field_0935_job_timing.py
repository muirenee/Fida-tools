from pathlib import Path

ROOT = Path('fida-field/app/src/main/java/com/fidalix/fidafield')
DB = ROOT / 'AppDatabase.java'
CLOUD = ROOT / 'CloudSyncFoundation.java'
MAIN = ROOT / 'MainActivity.java'
PDF = ROOT / 'ProfessionalPdfReport.java'
GRADLE = Path('fida-field/app/build.gradle')


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:160]!r}')
    path.write_text(text.replace(old, new, 1))


# Version bump.
replace_once(GRADLE, "versionCode 37\n        versionName '0.9.34-test'", "versionCode 38\n        versionName '0.9.35-test'")

# Local data model: durable epoch-millisecond timing fields, safe for offline and multi-device sync.
replace_once(DB, 'public static final int DB_VERSION = 10;', 'public static final int DB_VERSION = 11;')
replace_once(DB,
    'public int i(String k) { try { return Integer.parseInt(getOrDefault("id".equals(k)?"id":k, "0")); } catch (Exception e) { return 0; } }' if False else 'public int i(String k) { try { return Integer.parseInt(getOrDefault(k, "0")); } catch (Exception e) { return 0; } }',
    'public int i(String k) { try { return Integer.parseInt(getOrDefault(k, "0")); } catch (Exception e) { return 0; } }\n        public long l(String k) { try { return Long.parseLong(getOrDefault(k, "0")); } catch (Exception e) { return 0L; } }')
replace_once(DB,
    'job_date TEXT NOT NULL, next_service TEXT, signature_path TEXT, customer_name_signed TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL',
    'job_date TEXT NOT NULL, next_service TEXT, service_started_at_ms INTEGER DEFAULT 0, service_completed_at_ms INTEGER DEFAULT 0, service_duration_minutes INTEGER DEFAULT 0, signature_path TEXT, customer_name_signed TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL')
replace_once(DB,
    '        if(oldVersion<10){\n            db.execSQL("CREATE TABLE IF NOT EXISTS customer_sites (customer_id INTEGER NOT NULL, site_id INTEGER NOT NULL, PRIMARY KEY(customer_id,site_id), FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_customer ON customer_sites(customer_id,site_id)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_site ON customer_sites(site_id,customer_id)");\n            db.execSQL("INSERT OR IGNORE INTO customer_sites(customer_id,site_id) SELECT customer_id,id FROM sites WHERE customer_id IS NOT NULL");\n        }',
    '        if(oldVersion<10){\n            db.execSQL("CREATE TABLE IF NOT EXISTS customer_sites (customer_id INTEGER NOT NULL, site_id INTEGER NOT NULL, PRIMARY KEY(customer_id,site_id), FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE, FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_customer ON customer_sites(customer_id,site_id)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_customer_sites_site ON customer_sites(site_id,customer_id)");\n            db.execSQL("INSERT OR IGNORE INTO customer_sites(customer_id,site_id) SELECT customer_id,id FROM sites WHERE customer_id IS NOT NULL");\n        }\n        if(oldVersion<11){\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_started_at_ms INTEGER DEFAULT 0");\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_completed_at_ms INTEGER DEFAULT 0");\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_duration_minutes INTEGER DEFAULT 0");\n        }')

# Pull timing values from Supabase jobs.
replace_once(DB,
    'jt(v,o,"report_no","title","problem","diagnosis","work_done","parts","priority","status","job_date","next_service","customer_name_signed");v.put("technician",j(o,"technician_name"));',
    'jt(v,o,"report_no","title","problem","diagnosis","work_done","parts","priority","status","job_date","next_service","customer_name_signed");v.put("service_started_at_ms",o.optLong("service_started_at_ms",0L));v.put("service_completed_at_ms",o.optLong("service_completed_at_ms",0L));v.put("service_duration_minutes",o.optInt("service_duration_minutes",0));v.put("technician",j(o,"technician_name"));')

# Timing lifecycle methods. Completing preserves an existing finish timestamp when an already-completed job is edited.
replace_once(DB,
    '    public void setJobStatus(long jobId, String status) {\n        ContentValues v=new ContentValues();v.put("status",status);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");\n    }',
    '''    public void setJobStatus(long jobId, String status) {
        ContentValues v=new ContentValues();v.put("status",status);v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    public void startJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0||"Completed".equalsIgnoreCase(job.s("status")))return;ContentValues v=new ContentValues();if(job.l("service_started_at_ms")<=0)v.put("service_started_at_ms",System.currentTimeMillis());if("Open".equalsIgnoreCase(job.s("status")))v.put("status","In Progress");v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    public void completeJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0)return;long started=job.l("service_started_at_ms"),finished=job.l("service_completed_at_ms");if(finished<=0)finished=System.currentTimeMillis();int minutes=0;if(started>0&&finished>=started)minutes=(int)Math.max(0L,Math.round((finished-started)/60000.0));ContentValues v=new ContentValues();v.put("service_completed_at_ms",finished);v.put("service_duration_minutes",minutes);v.put("status","Completed");v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }''')

# Push timing values to Supabase.
replace_once(CLOUD,
    'else if("job".equals(type)){copy(o,r,"report_no","title","problem","diagnosis","work_done","parts","priority","status","customer_name_signed");o.put("technician_name",r.s("technician"));',
    'else if("job".equals(type)){copy(o,r,"report_no","title","problem","diagnosis","work_done","parts","priority","status","customer_name_signed");o.put("service_started_at_ms",r.l("service_started_at_ms"));o.put("service_completed_at_ms",r.l("service_completed_at_ms"));o.put("service_duration_minutes",r.i("service_duration_minutes"));o.put("technician_name",r.s("technician"));')

# Human-readable timing helpers in the Android UI.
replace_once(MAIN,
    '    private long parse(String s){try{return Long.parseLong(s==null||s.isEmpty()?"0":s);}catch(Exception e){return 0;}}\n    private void pickDate(EditText field){',
    '''    private long parse(String s){try{return Long.parseLong(s==null||s.isEmpty()?"0":s);}catch(Exception e){return 0;}}
    private String serviceTime(long millis){if(millis<=0)return "";return new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm",Locale.US).format(new java.util.Date(millis));}
    private String compactMinutes(long minutes){if(minutes<1)return "< 1 min";long h=minutes/60,m=minutes%60;if(h<=0)return m+" min";return h+" h"+(m>0?" "+m+" min":"");}
    private String serviceDuration(AppDatabase.Row job){long started=job.l("service_started_at_ms"),finished=job.l("service_completed_at_ms");if(started<=0)return "Not tracked";if(finished<=0){long minutes=Math.max(0L,(System.currentTimeMillis()-started)/60000L);return "In progress · "+compactMinutes(minutes);}return compactMinutes(Math.max(0,job.i("service_duration_minutes")));}
    private void pickDate(EditText field){''')

# Save-flow timing: setting In Progress starts timing; setting Completed stamps finish and duration.
old_save = 'try{long saved=db.saveJob(id,m,prefs.getString("report_prefix","FSR"));if("Completed".equals(String.valueOf(status.getSelectedItem()))&&a!=null&&a.id>0){String ns=val(next);if(ns.isEmpty())ns=db.suggestNextService(a.id,val(date));db.completeMaintenanceIfNeeded(a.id,saved,val(work),ns);}dialog.dismiss();toast("Job saved");showJobDetail(saved);}catch(Exception e){error("Could not save job",e);}'
new_save = 'try{long saved=db.saveJob(id,m,prefs.getString("report_prefix","FSR"));String selectedStatus=String.valueOf(status.getSelectedItem());if("In Progress".equals(selectedStatus)&&db.getJob(saved).l("service_started_at_ms")<=0)db.startJobService(saved);if("Completed".equals(selectedStatus))db.completeJobService(saved);if("Completed".equals(selectedStatus)&&a!=null&&a.id>0){String ns=val(next);if(ns.isEmpty())ns=db.suggestNextService(a.id,val(date));db.completeMaintenanceIfNeeded(a.id,saved,val(work),ns);}dialog.dismiss();toast("Job saved");showJobDetail(saved);}catch(Exception e){error("Could not save job",e);}'
replace_once(MAIN, old_save, new_save)

# Job detail timing panel and one-tap start action.
replace_once(MAIN,
    'b.addView(info("Service date",j.s("job_date")));b.addView(info("Technician",j.s("technician")));if(canSeeAllJobs())b.addView(info("Assignment control","Owner/Admin · reassignment allowed"));b.addView(info("Priority",j.s("priority")));\n        addIf(b,"Reported problem",j.s("problem"));',
    'b.addView(info("Service date",j.s("job_date")));b.addView(info("Technician",j.s("technician")));if(canSeeAllJobs())b.addView(info("Assignment control","Owner/Admin · reassignment allowed"));b.addView(info("Priority",j.s("priority")));\n        b.addView(section("Service timing"));b.addView(info("Started",serviceTime(j.l("service_started_at_ms")).isEmpty()?"Not started":serviceTime(j.l("service_started_at_ms"))));b.addView(info("Finished",serviceTime(j.l("service_completed_at_ms")).isEmpty()?"Not finished":serviceTime(j.l("service_completed_at_ms"))));b.addView(info("Duration",serviceDuration(j)));if(canModify&&!completed&&j.l("service_started_at_ms")<=0){MaterialButton startService=button("Start service now");startService.setOnClickListener(v->{db.startJobService(id);toast("Service timer started");showJobDetail(id);});b.addView(startService);}\n        addIf(b,"Reported problem",j.s("problem"));')
replace_once(MAIN, 'db.setJobStatus(id,"Completed");', 'db.completeJobService(id);')

# Keep About text current enough for field testing.
text = MAIN.read_text()
text = text.replace('Fida Field 0.9.23 Test\\nPeople access enable/disable controls, refined home dashboard and professional service reporting by Fidalix.', 'Fida Field 0.9.35 Test\\nOffline-first service timing, shared sites, team controls and professional field reporting by Fidalix.')
MAIN.write_text(text)

# PDF report includes service start, finish and duration when timing was tracked.
replace_once(PDF,
    '    public static File generate(Context context,AppDatabase db,long jobId,SharedPreferences prefs)throws Exception{',
    '''    private static String serviceTime(long millis){if(millis<=0)return "";return new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm",Locale.US).format(new java.util.Date(millis));}
    private static String serviceDuration(AppDatabase.Row j){long started=j.l("service_started_at_ms"),finished=j.l("service_completed_at_ms");if(started<=0)return "";long minutes=finished>0?Math.max(0,j.i("service_duration_minutes")):Math.max(0L,(System.currentTimeMillis()-started)/60000L);if(minutes<1)return "< 1 min";long h=minutes/60,m=minutes%60;String value=h>0?h+" h"+(m>0?" "+m+" min":""):m+" min";return finished>0?value:"In progress · "+value;}

    public static File generate(Context context,AppDatabase db,long jobId,SharedPreferences prefs)throws Exception{''')
replace_once(PDF,
    'w.section("Report details");w.two("Report number",j.s("report_no"),"Priority",j.s("priority"));w.two("Service date",j.s("job_date"),"Technician",j.s("technician"));',
    'w.section("Report details");w.two("Report number",j.s("report_no"),"Priority",j.s("priority"));w.two("Service date",j.s("job_date"),"Technician",j.s("technician"));w.two("Service started",serviceTime(j.l("service_started_at_ms")),"Service finished",serviceTime(j.l("service_completed_at_ms")));w.field("Service duration",serviceDuration(j));')

print('Fida Field 0.9.35 job timing patch applied')
