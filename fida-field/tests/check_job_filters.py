"""Exercise the production Java query builders against SQLite fixtures.
Requires Python 3 + JDK 17; no Android SDK needed. Does not replace Android lint/UI QA.
"""
import base64
from pathlib import Path
import sqlite3
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'app/src/main/java/com/fidalix/fidafield'
source = (SRC / 'AppDatabase.java').read_text()

def method(start, end):
    return source[source.index(start):source.index(end, source.index(start))]

methods = '\n'.join([
    method('    public List<Row> jobsFiltered(', '    public List<Row> jobsForCustomer('),
    method('    private void appendJobScope(', '    public boolean jobVisibleToUser('),
    method('    public long visibleOpenJobCount(', '    private long countSql('),
    method('    public List<Row> jobsFilteredScoped(', '    public List<Row> jobsForCustomerScoped('),
])
probe = '''package com.fidalix.fidafield;
import java.util.*;
public class QueryProbe {
    static class Row {}
    static void emit(String sql,String[] args){
        Base64.Encoder encoder=Base64.getEncoder();
        System.out.print(encoder.encodeToString(sql.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        if(args!=null)for(String arg:args)System.out.print("\\t"+encoder.encodeToString(arg.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        System.out.println();
    }
    List<Row> rows(String sql,String[] args){emit(sql,args);return new ArrayList<>();}
    long countSql(String sql,String[] args){emit(sql,args);return 0;}
    long count(String table,String where,String[] args){return countSql("SELECT COUNT(*) FROM "+table+" WHERE "+where,args);}
''' + methods + '''
    public static void main(String[] args){
        QueryProbe p=new QueryProbe();
        p.visibleOpenJobCount("alice",true);
        p.jobsFilteredScoped("",JobStatusFilter.ACTIVE,"All","All","","","alice",true);
        p.visibleOpenJobCount("alice",false);
        p.jobsFilteredScoped("",JobStatusFilter.ACTIVE,"All","All","","","alice",false);
        p.jobsFilteredScoped("","In Progress","All","All","","","alice",false);
        p.jobsFilteredScoped("","Cancelled","All","All","","","alice",false);
        p.jobsFilteredScoped("pump",JobStatusFilter.ACTIVE,"High","All","2026-09-01","2026-09-30","alice",false);
        p.jobsFilteredScoped("",JobStatusFilter.ACTIVE,"All","All","","","unknown",false);
        p.jobsFiltered("",JobStatusFilter.ACTIVE,"All","All","","");
    }
}
'''
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)
    (path/'QueryProbe.java').write_text(probe)
    compiler=['javac'] if shutil.which('javac') else ['java','-m','jdk.compiler/com.sun.tools.javac.Main']
    subprocess.run(compiler+['-d',tmp,str(path/'QueryProbe.java'),str(SRC/'JobStatusFilter.java')],check=True)
    result=subprocess.run(['java','-cp',tmp,'com.fidalix.fidafield.QueryProbe'],check=True,capture_output=True,text=True)

conn=sqlite3.connect(':memory:')
conn.executescript('''
CREATE TABLE technicians(id INTEGER, user_uuid TEXT);
INSERT INTO technicians VALUES(1,'alice'),(2,'bob');
CREATE TABLE customers(id INTEGER,name TEXT);
CREATE TABLE sites(id INTEGER,name TEXT);
CREATE TABLE assets(id INTEGER,name TEXT,tag TEXT);
CREATE TABLE jobs(id INTEGER,status TEXT,technician_id INTEGER,technician TEXT,
 report_no TEXT,title TEXT,problem TEXT,priority TEXT,job_date TEXT,
 customer_id INTEGER,site_id INTEGER,asset_id INTEGER);
INSERT INTO jobs VALUES
 (1,'Open',1,'Alice','FSR-1','Pump','Leak','High','2026-09-18',0,0,0),
 (2,'In Progress',1,'Alice','FSR-2','Router','','Normal','2026-09-17',0,0,0),
 (3,'Completed',1,'Alice','FSR-3','Pump','','High','2026-09-18',0,0,0),
 (4,'Cancelled',1,'Alice','FSR-4','Pump','','High','2026-09-18',0,0,0),
 (5,'Open',2,'Bob','FSR-5','Pump','','High','2026-09-18',0,0,0);
''')
results=[]
for line in result.stdout.splitlines():
    sql,*args=[base64.b64decode(part).decode() for part in line.split('\t')]
    results.append([row[0] for row in conn.execute(sql,args)])
expected=[[3],[5,1,2],[2],[1,2],[2],[4],[1],[],[5,1,2]]
assert results==expected, (results,expected)
print('PASS: 9 production-query checks; counts match lists, cancelled/completed excluded, role scope and combined filters preserved.')
