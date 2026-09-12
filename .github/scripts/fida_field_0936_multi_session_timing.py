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
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:180]!r}')
    path.write_text(text.replace(old, new, 1))


# Version bump.
replace_once(GRADLE, "versionCode 38\n        versionName '0.9.35-test'", "versionCode 39\n        versionName '0.9.36-test'")

# Local job model: keep the 0.9.35 summary fields for compatibility, but make the
# canonical timing source a list of active-work sessions. This supports multi-day jobs
# and paused periods without counting overnight / waiting time as service duration.
replace_once(DB, 'public static final int DB_VERSION = 11;', 'public static final int DB_VERSION = 12;')
replace_once(DB,
    'service_started_at_ms INTEGER DEFAULT 0, service_completed_at_ms INTEGER DEFAULT 0, service_duration_minutes INTEGER DEFAULT 0, signature_path TEXT',
    "service_started_at_ms INTEGER DEFAULT 0, service_completed_at_ms INTEGER DEFAULT 0, service_duration_minutes INTEGER DEFAULT 0, service_sessions_json TEXT NOT NULL DEFAULT '[]', signature_path TEXT")
replace_once(DB,
    '        if(oldVersion<11){\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_started_at_ms INTEGER DEFAULT 0");\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_completed_at_ms INTEGER DEFAULT 0");\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_duration_minutes INTEGER DEFAULT 0");\n        }',
    '        if(oldVersion<11){\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_started_at_ms INTEGER DEFAULT 0");\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_completed_at_ms INTEGER DEFAULT 0");\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_duration_minutes INTEGER DEFAULT 0");\n        }\n        if(oldVersion<12){\n            db.execSQL("ALTER TABLE jobs ADD COLUMN service_sessions_json TEXT NOT NULL DEFAULT \'[]\'");\n        }')

# Pull canonical sessions from Supabase. Old 0.9.35 rows remain supported by lazy
# conversion from service_started_at_ms/service_completed_at_ms.
replace_once(DB,
    'jt(v,o,"report_no","title","problem","diagnosis","work_done","parts","priority","status","job_date","next_service","customer_name_signed");v.put("service_started_at_ms",o.optLong("service_started_at_ms",0L));v.put("service_completed_at_ms",o.optLong("service_completed_at_ms",0L));v.put("service_duration_minutes",o.optInt("service_duration_minutes",0));v.put("technician",j(o,"technician_name"));',
    'jt(v,o,"report_no","title","problem","diagnosis","work_done","parts","priority","status","job_date","next_service","customer_name_signed");v.put("service_started_at_ms",o.optLong("service_started_at_ms",0L));v.put("service_completed_at_ms",o.optLong("service_completed_at_ms",0L));v.put("service_duration_minutes",o.optInt("service_duration_minutes",0));JSONArray timingSessions=o.optJSONArray("service_sessions");v.put("service_sessions_json",timingSessions==null?"[]":timingSessions.toString());v.put("technician",j(o,"technician_name"));')

old_timing = '''    public void startJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0||"Completed".equalsIgnoreCase(job.s("status")))return;ContentValues v=new ContentValues();if(job.l("service_started_at_ms")<=0)v.put("service_started_at_ms",System.currentTimeMillis());if("Open".equalsIgnoreCase(job.s("status")))v.put("status","In Progress");v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    public void completeJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0)return;long started=job.l("service_started_at_ms"),finished=job.l("service_completed_at_ms");if(finished<=0)finished=System.currentTimeMillis();int minutes=0;if(started>0&&finished>=started)minutes=(int)Math.max(0L,Math.round((finished-started)/60000.0));ContentValues v=new ContentValues();v.put("service_completed_at_ms",finished);v.put("service_duration_minutes",minutes);v.put("status","Completed");v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }'''

new_timing = '''    private JSONArray normalizedServiceSessions(Row job){
        JSONArray out=new JSONArray();String raw=job.s("service_sessions_json");
        if(raw!=null&&!raw.trim().isEmpty())try{JSONArray parsed=new JSONArray(raw);for(int i=0;i<parsed.length();i++){JSONObject src=parsed.optJSONObject(i);if(src==null)continue;long start=src.optLong("started_at_ms",0L);if(start<=0)continue;JSONObject copy=new JSONObject();copy.put("id",src.optString("id","session-"+(i+1)));copy.put("started_at_ms",start);copy.put("ended_at_ms",Math.max(0L,src.optLong("ended_at_ms",0L)));out.put(copy);}}catch(Exception ignored){}
        if(out.length()==0&&job.l("service_started_at_ms")>0)try{out.put(new JSONObject().put("id","legacy-"+job.id()).put("started_at_ms",job.l("service_started_at_ms")).put("ended_at_ms",Math.max(0L,job.l("service_completed_at_ms"))));}catch(Exception ignored){}
        return out;
    }

    public JSONArray jobServiceSessions(long jobId){Row job=getJob(jobId);return job.id()==0?new JSONArray():normalizedServiceSessions(job);}
    private int activeServiceSession(JSONArray sessions){for(int i=sessions.length()-1;i>=0;i--){JSONObject s=sessions.optJSONObject(i);if(s!=null&&s.optLong("started_at_ms",0L)>0&&s.optLong("ended_at_ms",0L)<=0)return i;}return -1;}
    private long serviceMillis(JSONArray sessions,long nowMs){long total=0L;for(int i=0;i<sessions.length();i++){JSONObject s=sessions.optJSONObject(i);if(s==null)continue;long start=s.optLong("started_at_ms",0L),end=s.optLong("ended_at_ms",0L);if(start<=0)continue;if(end<=0)end=nowMs;if(end>start)total+=end-start;}return Math.max(0L,total);}
    public boolean jobServiceRunning(long jobId){return activeServiceSession(jobServiceSessions(jobId))>=0;}
    public long jobServiceDurationMinutes(long jobId){JSONArray sessions=jobServiceSessions(jobId);long ms=serviceMillis(sessions,System.currentTimeMillis());return Math.max(0L,ms/60000L);}
    private String sessionDurationText(long millis){if(millis<=0)return "< 1 min";long minutes=millis/60000L;if(minutes<1)return "< 1 min";long h=minutes/60,m=minutes%60;return h>0?h+" h"+(m>0?" "+m+" min":""):m+" min";}
    public String jobServiceSessionSummary(long jobId){JSONArray sessions=jobServiceSessions(jobId);if(sessions.length()==0)return "";StringBuilder b=new StringBuilder();java.text.SimpleDateFormat fmt=new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm",Locale.US);long nowMs=System.currentTimeMillis();for(int i=0;i<sessions.length();i++){JSONObject s=sessions.optJSONObject(i);if(s==null)continue;long start=s.optLong("started_at_ms",0L),end=s.optLong("ended_at_ms",0L);if(start<=0)continue;if(b.length()>0)b.append("\\n");long effectiveEnd=end>0?end:nowMs;b.append("Session ").append(i+1).append(": ").append(fmt.format(new java.util.Date(start))).append(" → ").append(end>0?fmt.format(new java.util.Date(end)):"Running").append(" (").append(sessionDurationText(Math.max(0L,effectiveEnd-start))).append(")");}return b.toString();}

    private void persistServiceSessions(long jobId,JSONArray sessions,boolean completed){
        Row job=getJob(jobId);if(job.id()==0)return;long nowMs=System.currentTimeMillis(),first=0L;for(int i=0;i<sessions.length();i++){JSONObject s=sessions.optJSONObject(i);if(s==null)continue;long start=s.optLong("started_at_ms",0L);if(start>0&&(first<=0||start<first))first=start;}if(first<=0)first=job.l("service_started_at_ms");long activeMs=serviceMillis(sessions,nowMs);ContentValues v=new ContentValues();v.put("service_sessions_json",sessions.toString());v.put("service_started_at_ms",Math.max(0L,first));v.put("service_duration_minutes",Math.max(0L,activeMs/60000L));if(completed){v.put("service_completed_at_ms",nowMs);v.put("status","Completed");}else{v.put("service_completed_at_ms",0L);if(!"Cancelled".equalsIgnoreCase(job.s("status")))v.put("status","In Progress");}v.put("updated_at",now());getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});queueSync("job",jobId,"upsert");
    }

    public void startJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0||"Completed".equalsIgnoreCase(job.s("status")))return;JSONArray sessions=normalizedServiceSessions(job);if(activeServiceSession(sessions)>=0)return;try{sessions.put(new JSONObject().put("id",java.util.UUID.randomUUID().toString()).put("started_at_ms",System.currentTimeMillis()).put("ended_at_ms",0L));}catch(Exception ignored){}persistServiceSessions(jobId,sessions,false);
    }

    public void pauseJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0||"Completed".equalsIgnoreCase(job.s("status")))return;JSONArray sessions=normalizedServiceSessions(job);int active=activeServiceSession(sessions);if(active<0)return;JSONObject s=sessions.optJSONObject(active);if(s!=null)try{s.put("ended_at_ms",System.currentTimeMillis());}catch(Exception ignored){}persistServiceSessions(jobId,sessions,false);
    }

    public void completeJobService(long jobId){
        Row job=getJob(jobId);if(job.id()==0)return;JSONArray sessions=normalizedServiceSessions(job);int active=activeServiceSession(sessions);if(active>=0){JSONObject s=sessions.optJSONObject(active);if(s!=null)try{s.put("ended_at_ms",System.currentTimeMillis());}catch(Exception ignored){}}persistServiceSessions(jobId,sessions,true);
    }'''
replace_once(DB, old_timing, new_timing)

# Push sessions as JSON together with the job row. The existing job-level conflict guard
# prevents two devices from silently overwriting unsynced local timing edits.
replace_once(CLOUD,
    'else if("job".equals(type)){copy(o,r,"report_no","title","problem","diagnosis","work_done","parts","priority","status","customer_name_signed");o.put("service_started_at_ms",r.l("service_started_at_ms"));o.put("service_completed_at_ms",r.l("service_completed_at_ms"));o.put("service_duration_minutes",r.i("service_duration_minutes"));o.put("technician_name",r.s("technician"));',
    'else if("job".equals(type)){copy(o,r,"report_no","title","problem","diagnosis","work_done","parts","priority","status","customer_name_signed");o.put("service_started_at_ms",r.l("service_started_at_ms"));o.put("service_completed_at_ms",r.l("service_completed_at_ms"));o.put("service_duration_minutes",r.i("service_duration_minutes"));o.put("service_sessions",db.jobServiceSessions(r.id()));o.put("technician_name",r.s("technician"));')

# UI duration is now active-work time only. Paused time (including overnight or waiting
# for parts/customer access) is not added to the total.
replace_once(MAIN,
    '    private String serviceDuration(AppDatabase.Row job){long started=job.l("service_started_at_ms"),finished=job.l("service_completed_at_ms");if(started<=0)return "Not tracked";if(finished<=0){long minutes=Math.max(0L,(System.currentTimeMillis()-started)/60000L);return "In progress · "+compactMinutes(minutes);}return compactMinutes(Math.max(0,job.i("service_duration_minutes")));}',
    '    private String serviceDuration(AppDatabase.Row job){if(job.l("service_started_at_ms")<=0)return "Not tracked";String value=compactMinutes(db.jobServiceDurationMinutes(job.id()));if(job.l("service_completed_at_ms")>0)return value;return (db.jobServiceRunning(job.id())?"Running · ":"Paused · ")+value;}')

old_panel = '        b.addView(section("Service timing"));b.addView(info("Started",serviceTime(j.l("service_started_at_ms")).isEmpty()?"Not started":serviceTime(j.l("service_started_at_ms"))));b.addView(info("Finished",serviceTime(j.l("service_completed_at_ms")).isEmpty()?"Not finished":serviceTime(j.l("service_completed_at_ms"))));b.addView(info("Duration",serviceDuration(j)));if(canModify&&!completed&&j.l("service_started_at_ms")<=0){MaterialButton startService=button("Start service now");startService.setOnClickListener(v->{db.startJobService(id);toast("Service timer started");showJobDetail(id);});b.addView(startService);}'
new_panel = '''        b.addView(section("Service timing"));boolean serviceRunning=db.jobServiceRunning(id);JSONArray serviceSessions=db.jobServiceSessions(id);String timerState=completed?"Completed":serviceRunning?"Running":j.l("service_started_at_ms")>0?"Paused":"Not started";b.addView(info("Timer status",timerState));b.addView(info("First started",serviceTime(j.l("service_started_at_ms")).isEmpty()?"Not started":serviceTime(j.l("service_started_at_ms"))));b.addView(info("Finished",serviceTime(j.l("service_completed_at_ms")).isEmpty()?"Not finished":serviceTime(j.l("service_completed_at_ms"))));b.addView(info("Active service duration",serviceDuration(j)));b.addView(info("Work sessions",String.valueOf(serviceSessions.length())));if(canModify&&!completed){MaterialButton timingAction=button(j.l("service_started_at_ms")<=0?"Start service now":serviceRunning?"Pause service":"Resume service");timingAction.setOnClickListener(v->{if(db.jobServiceRunning(id)){db.pauseJobService(id);toast("Service timer paused");}else{db.startJobService(id);toast(j.l("service_started_at_ms")<=0?"Service timer started":"Service timer resumed");}showJobDetail(id);});b.addView(timingAction);}if(serviceSessions.length()>0){b.addView(section("Work sessions"));for(int si=0;si<serviceSessions.length();si++){JSONObject ss=serviceSessions.optJSONObject(si);if(ss==null)continue;long st=ss.optLong("started_at_ms",0L),en=ss.optLong("ended_at_ms",0L),endForDuration=en>0?en:System.currentTimeMillis();String when=serviceTime(st)+" → "+(en>0?serviceTime(en):"Running");long mins=Math.max(0L,(endForDuration-st)/60000L);b.addView(rowCard("Session "+(si+1),when,compactMinutes(mins)));}}'''
replace_once(MAIN, old_panel, new_panel)

# About text.
text = MAIN.read_text().replace('Fida Field 0.9.35 Test\\nOffline-first service timing, shared sites, team controls and professional field reporting by Fidalix.', 'Fida Field 0.9.36 Test\\nPause/resume multi-session service timing, shared sites, team controls and professional field reporting by Fidalix.')
MAIN.write_text(text)

# PDF shows active-work duration plus each session so multi-day work remains auditable.
replace_once(PDF,
    '    private static String serviceDuration(AppDatabase.Row j){long started=j.l("service_started_at_ms"),finished=j.l("service_completed_at_ms");if(started<=0)return "";long minutes=finished>0?Math.max(0,j.i("service_duration_minutes")):Math.max(0L,(System.currentTimeMillis()-started)/60000L);if(minutes<1)return "< 1 min";long h=minutes/60,m=minutes%60;String value=h>0?h+" h"+(m>0?" "+m+" min":""):m+" min";return finished>0?value:"In progress · "+value;}',
    '    private static String serviceDuration(AppDatabase db,AppDatabase.Row j){if(j.l("service_started_at_ms")<=0)return "";long minutes=db.jobServiceDurationMinutes(j.id());String value;if(minutes<1)value="< 1 min";else{long h=minutes/60,m=minutes%60;value=h>0?h+" h"+(m>0?" "+m+" min":""):m+" min";}if(j.l("service_completed_at_ms")>0)return value;return (db.jobServiceRunning(j.id())?"Running · ":"Paused · ")+value;}')
replace_once(PDF,
    'w.section("Report details");w.two("Report number",j.s("report_no"),"Priority",j.s("priority"));w.two("Service date",j.s("job_date"),"Technician",j.s("technician"));w.two("Service started",serviceTime(j.l("service_started_at_ms")),"Service finished",serviceTime(j.l("service_completed_at_ms")));w.field("Service duration",serviceDuration(j));',
    'w.section("Report details");w.two("Report number",j.s("report_no"),"Priority",j.s("priority"));w.two("Service date",j.s("job_date"),"Technician",j.s("technician"));w.two("First service start",serviceTime(j.l("service_started_at_ms")),"Service finished",serviceTime(j.l("service_completed_at_ms")));w.field("Active service duration",serviceDuration(db,j));w.field("Work sessions",db.jobServiceSessionSummary(jobId));')

print('Fida Field 0.9.36 multi-session timing patch applied')
