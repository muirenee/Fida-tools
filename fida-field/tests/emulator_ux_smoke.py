"""UI smoke checks on a disposable Android emulator; never use on a real device."""
import datetime
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

PKG='com.fidalix.fidafield'
OUT=Path('emulator-evidence'); OUT.mkdir(exist_ok=True)
checks=[]

def adb(*args, data=None, check=True):
    return subprocess.run(['adb',*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=check,timeout=60).stdout

def shell(*args):
    return adb('shell',*args).decode().strip()

def tree():
    for attempt in range(3):
        try:
            shell('uiautomator','dump','/sdcard/fida-ui.xml')
            return ET.fromstring(adb('exec-out','cat','/sdcard/fida-ui.xml'))
        except Exception:
            if attempt==2: raise
            time.sleep(1)

def match(node,text):
    return node.get('text')==text or node.get('content-desc')==text

def find(text,scroll=False):
    for attempt in range(7 if scroll else 1):
        nodes=[n for n in tree().iter('node') if match(n,text)]
        if nodes: return nodes[-1]
        if scroll: shell('input','swipe','520','1550','520','650','350')
    raise AssertionError('UI target missing: '+text)

def tap(text,scroll=False):
    n=find(text,scroll)
    x1,y1,x2,y2=map(int,re.findall(r'\d+',n.get('bounds')))
    assert x2>x1 and y2>y1, ('Empty bounds',text)
    shell('input','tap',str((x1+x2)//2),str((y1+y2)//2))
    time.sleep(.4)

def expect(text):
    find(text)
    checks.append(text)
    print('PASS:',text,flush=True)

def shot(name):
    (OUT/(name+'.png')).write_bytes(adb('exec-out','screencap','-p'))
    (OUT/(name+'.xml')).write_bytes(ET.tostring(tree()))

def launch():
    shell('am','start','-W','-n',PKG+'/.FidaFieldActivity');time.sleep(2)

def stop(): shell('am','force-stop',PKG)

def prefs(role='Owner'):
    stop()
    xml=ET.fromstring(adb('exec-out','run-as',PKG,'cat','shared_prefs/fida_field_prefs.xml'))
    values={'workspace_id':'emulator-only','workspace_name':'UX Test Workspace','account_role':role,'cloud_user_id':'ux-alice'}
    for key,value in values.items():
        for n in list(xml):
            if n.get('name')==key: xml.remove(n)
        ET.SubElement(xml,'string',name=key).text=value
    path=OUT/'test-prefs.xml';path.write_bytes(ET.tostring(xml,encoding='utf-8',xml_declaration=True))
    adb('push',str(path),'/data/local/tmp/fida-test-prefs.xml')
    shell('run-as',PKG,'cp','/data/local/tmp/fida-test-prefs.xml','shared_prefs/fida_field_prefs.xml')

def seed():
    stop()
    dbfile=OUT/'fixture.db'
    dbfile.write_bytes(adb('exec-out','run-as',PKG,'cat','databases/fida_field.db'))
    for suffix in ['-wal','-shm']:
        r=subprocess.run(['adb','exec-out','run-as',PKG,'cat','databases/fida_field.db'+suffix],capture_output=True)
        if r.returncode==0: Path(str(dbfile)+suffix).write_bytes(r.stdout)
    db=sqlite3.connect(dbfile)
    day=datetime.date.today().isoformat()
    db.execute("INSERT INTO customers(id,name,contact,phone,created_at) VALUES(1,?,?,?,?)",('Kigali Technical Services — Long Customer Name','Test Contact','+250 780 123 456',day))
    db.execute("INSERT INTO assets(id,customer_id,tag,name,serial,next_service,created_at) VALUES(1,1,'PUMP-001','Booster pump and monitoring controller','UX-SERIAL-01',?,?)",(day,day))
    db.execute("INSERT INTO technicians(id,name,user_uuid,active,created_at) VALUES(1,'Alice','ux-alice',1,?)",(day,))
    db.execute("INSERT INTO technicians(id,name,user_uuid,active,created_at) VALUES(2,'Bob','ux-bob',1,?)",(day,))
    for i,(status,title,tech) in enumerate([('Open','Pump inspection',1),('In Progress','Network service',1),('Completed','Completed service',1),('Cancelled','Cancelled visit',1),('Open','Other technician job',2)],1):
        db.execute('INSERT INTO jobs(id,report_no,customer_id,asset_id,title,technician_id,technician,status,priority,job_date,created_at,updated_at) VALUES(?,?,1,1,?,?,?,?,?,?,?,?)',(i,'UX-'+str(i),title,tech,'Alice' if tech==1 else 'Bob',status,'Normal',day,day,day))
    db.commit();db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.execute('PRAGMA journal_mode=DELETE');db.close()
    adb('push',str(dbfile),'/data/local/tmp/fida-test.db')
    shell('run-as',PKG,'rm','-f','databases/fida_field.db-wal','databases/fida_field.db-shm')
    shell('run-as',PKG,'cp','/data/local/tmp/fida-test.db','databases/fida_field.db')
    prefs()

def main():
    assert shell('getprop','ro.kernel.qemu')=='1','Requires a disposable emulator'
    shell('wm','size','1080x1920');shell('wm','density','360')
    adb('install','-r',sys.argv[1]);shell('pm','clear',PKG)
    shell('pm','grant',PKG,'android.permission.POST_NOTIFICATIONS')
    launch();expect('Welcome to Fida Field');shot('01-welcome')
    tap('Use Fida Field locally',scroll=True);expect('Fida Field')
    seed();launch();expect('Active jobs');shot('02-dashboard-light')
    tap('Active jobs');expect('3 jobs');shot('03-active-jobs')
    assert not any(n.get('text','').startswith('UX-4') for n in tree().iter('node'))
    tap('More filters');expect('Hide filters');tap('Hide filters');expect('More filters')
    tap('Search jobs');shell('input','text','Pump');shell('input','keyevent','66');time.sleep(.5)
    tap('Jobs');expect('Pump');expect('1 job');shot('04-job-search')
    tap('UX-1 · Pump inspection',scroll=True);expect('UX-1');shot('05-job-detail')
    shell('input','keyevent','4');expect('Pump');expect('1 job')
    tap('Customers');expect('Search customers & sites')
    tap('Search customers & sites');shell('input','text','Kigali');shell('input','keyevent','4')
    tap('Assets');tap('Customers');expect('Kigali');shot('06-customers')
    tap('Assets');tap('Search assets, tags & serials');shell('input','text','PUMP');shell('input','keyevent','4')
    tap('Jobs');tap('Assets');expect('PUMP');shot('07-assets')
    tap('Jobs');tap('Clear search & filters');expect('5 jobs')
    tap('Search jobs');shell('input','text','NoSuchJob');shell('input','keyevent','4')
    expect('No jobs match this view. Try another search or clear the filters.')
    tap('Clear search jobs');expect('5 jobs')
    prefs('Technician');launch();expect('My active jobs');tap('In progress');expect('1 job');expect('In Progress');shot('08-technician-in-progress')
    tap('Home');tap('My active jobs');expect('2 jobs');shot('09-technician-active')
    prefs('Viewer');launch();tap('Jobs');expect('Viewer access is read-only. You can review jobs available to your account.');shot('10-viewer')
    prefs();shell('cmd','uimode','night','yes');launch();shot('11-dashboard-dark');tap('Jobs');shot('12-jobs-dark')
    shell('settings','put','system','font_scale','1.3');stop();launch();shot('13-large-text');tap('Jobs');shot('14-large-text-jobs')
    shell('settings','put','system','font_scale','1.0');shell('cmd','uimode','night','no')
    shell('wm','size','1600x2560');shell('wm','density','240');stop();launch();shot('15-tablet-dashboard');tap('Jobs');shot('16-tablet-jobs')
    (OUT/'results.json').write_text(json.dumps({'status':'passed','checks':checks,'scope':'Android API 35 emulator; local fixtures; cloud operations, camera and signatures not tested'},indent=2))

try:
    main()
except Exception:
    try: shot('failure')
    except Exception: pass
    raise
finally:
    (OUT/'logcat.txt').write_bytes(adb('logcat','-d','-t','800',check=False))
    # Fixture contents are synthetic; no customer data or auth credentials are used.
