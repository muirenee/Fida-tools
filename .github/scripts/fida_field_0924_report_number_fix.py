from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

app = Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
s = app.read_text()

old_save = '''    public long saveJob(long id, Map<String,String> m, String prefix) {
        Row before=id>0?one("SELECT technician_id,technician FROM jobs WHERE id=?",new String[]{String.valueOf(id)}):new Row();long oldTech=before.i("technician_id");
        ContentValues v=cv(m,"title","problem","diagnosis","work_done","parts","technician","priority","status","job_date","next_service","customer_name_signed"); putLong(v,"customer_id",m.get("customer_id")); putLong(v,"site_id",m.get("site_id")); putLong(v,"asset_id",m.get("asset_id")); putLong(v,"technician_id",m.get("technician_id")); v.put("updated_at",now());long saved=id;
        if(id==0){v.put("report_no",nextReportNo(prefix));v.put("created_at",now());saved=getWritableDatabase().insertOrThrow("jobs",null,v);}else getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(id)});long newTech=0;try{newTech=Long.parseLong(m.getOrDefault("technician_id","0"));}catch(Exception ignored){}if(saved>0&&oldTech!=newTech)recordLocalAssignment(saved,oldTech,newTech,m.getOrDefault("assignment_actor","Local user"));queueSync("job",saved,"upsert");return saved;
    }
'''

new_save = '''    public long saveJob(long id, Map<String,String> m, String prefix) {
        Row before=id>0?one("SELECT technician_id,technician FROM jobs WHERE id=?",new String[]{String.valueOf(id)}):new Row();long oldTech=before.i("technician_id");
        ContentValues v=cv(m,"title","problem","diagnosis","work_done","parts","technician","priority","status","job_date","next_service","customer_name_signed"); putLong(v,"customer_id",m.get("customer_id")); putLong(v,"site_id",m.get("site_id")); putLong(v,"asset_id",m.get("asset_id")); putLong(v,"technician_id",m.get("technician_id")); v.put("updated_at",now());long saved=id;
        if(id==0){
            v.put("created_at",now());android.database.sqlite.SQLiteConstraintException last=null;
            for(int attempt=0;attempt<8;attempt++){
                v.put("report_no",nextReportNo(prefix));
                try{saved=getWritableDatabase().insertOrThrow("jobs",null,v);last=null;break;}
                catch(android.database.sqlite.SQLiteConstraintException e){last=e;}
            }
            if(saved<=0&&last!=null)throw last;
        }else getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(id)});long newTech=0;try{newTech=Long.parseLong(m.getOrDefault("technician_id","0"));}catch(Exception ignored){}if(saved>0&&oldTech!=newTech)recordLocalAssignment(saved,oldTech,newTech,m.getOrDefault("assignment_actor","Local user"));queueSync("job",saved,"upsert");return saved;
    }
'''
s = replace_once(s, old_save, new_save, 'saveJob collision retry')

old_next = '''    public synchronized String nextReportNo(String prefix) {
        SQLiteDatabase db=getWritableDatabase(); int y=Calendar.getInstance().get(Calendar.YEAR); int seq=1;
        db.beginTransaction();
        try {
            Cursor c=db.rawQuery("SELECT seq FROM sequences WHERE year=?",new String[]{String.valueOf(y)});
            try{if(c.moveToFirst())seq=c.getInt(0)+1;}finally{c.close();}
            ContentValues v=new ContentValues();v.put("year",y);v.put("seq",seq);db.insertWithOnConflict("sequences",null,v,SQLiteDatabase.CONFLICT_REPLACE);db.setTransactionSuccessful();
        } finally {db.endTransaction();}
        String p=(prefix==null||prefix.trim().isEmpty())?"FSR":prefix.trim().toUpperCase(Locale.US);
        return String.format(Locale.US,"%s-%d-%05d",p,y,seq);
    }
'''

new_next = '''    public synchronized String nextReportNo(String prefix) {
        String p=(prefix==null||prefix.trim().isEmpty())?"FSR":prefix.trim().toUpperCase(Locale.US);
        int y=Calendar.getInstance().get(Calendar.YEAR);String stem=p+"-"+y+"-";SQLiteDatabase db=getWritableDatabase();int seq=0;String candidate;
        db.beginTransaction();
        try {
            Cursor c=db.rawQuery("SELECT seq FROM sequences WHERE year=?",new String[]{String.valueOf(y)});
            try{if(c.moveToFirst())seq=Math.max(seq,c.getInt(0));}finally{c.close();}
            Cursor jobs=db.rawQuery("SELECT report_no FROM jobs WHERE report_no LIKE ?",new String[]{stem+"%"});
            try{while(jobs.moveToNext()){String report=jobs.getString(0);if(report==null||!report.startsWith(stem))continue;try{seq=Math.max(seq,Integer.parseInt(report.substring(stem.length())));}catch(Exception ignored){}}}finally{jobs.close();}
            do{seq++;candidate=String.format(Locale.US,"%s%05d",stem,seq);}while(countSql("SELECT COUNT(*) FROM jobs WHERE report_no=?",new String[]{candidate})>0);
            ContentValues v=new ContentValues();v.put("year",y);v.put("seq",seq);db.insertWithOnConflict("sequences",null,v,SQLiteDatabase.CONFLICT_REPLACE);db.setTransactionSuccessful();
            return candidate;
        } finally {db.endTransaction();}
    }
'''
s = replace_once(s, old_next, new_next, 'nextReportNo reconciliation')
app.write_text(s)

main = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
m = main.read_text()
m = m.replace('Fida Field 0.9.23 Test\\nMember app-access controls, field assignment controls and workspace refinements by Fidalix.', 'Fida Field 0.9.24 Test\\nCollision-safe report numbering, member app-access controls and workspace refinements by Fidalix.')
m = m.replace('Fida Field 0.9.23 Test\\nRefined home dashboard, consistent customer terminology, professional reports and customer email delivery by Fidalix.', 'Fida Field 0.9.24 Test\\nCollision-safe report numbering, refined dashboard and professional service reports by Fidalix.')
main.write_text(m)

gradle = Path('fida-field/app/build.gradle')
g = gradle.read_text()
g = replace_once(g, 'versionCode 26', 'versionCode 27', 'versionCode')
g = replace_once(g, "versionName '0.9.23-test'", "versionName '0.9.24-test'", 'versionName')
gradle.write_text(g)

print('Applied Fida Field 0.9.24 report-number collision fix')
