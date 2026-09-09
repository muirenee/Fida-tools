package com.fidalix.fidafield;

import android.content.SharedPreferences;

import java.util.UUID;

/** Offline-first synchronization state. Local changes are never discarded before a
 * backend acknowledges them. */
public class CloudSyncFoundation {
    public static final String PROVIDER="Supabase";
    private final SharedPreferences prefs;
    private final AppDatabase db;

    public CloudSyncFoundation(SharedPreferences prefs,AppDatabase db){this.prefs=prefs;this.db=db;}

    public String deviceId(){String id=prefs.getString("cloud_device_id","");if(id==null||id.isEmpty()){id=UUID.randomUUID().toString();prefs.edit().putString("cloud_device_id",id).apply();}return id;}
    public long pendingChanges(){return db.count("sync_queue",null,null);}
    public String providerName(){return PROVIDER;}
    public boolean backendConfigured(){return !prefs.getString("supabase_url","").trim().isEmpty()&&!prefs.getString("supabase_anon_key","").trim().isEmpty();}
    public boolean signedIn(){return backendConfigured()&&!prefs.getString("cloud_access_token","").isEmpty();}
    public String accountEmail(){return prefs.getString("cloud_account_email","");}
    public String lastSync(){String v=prefs.getString("cloud_last_sync","");return v.isEmpty()?"Never":v;}
    public String lastResult(){return prefs.getString("cloud_last_result","Not connected");}
    public String backendStatus(){if(!backendConfigured())return "Not configured";return signedIn()?"Connected":"Configured · sign-in required";}
    public void markSyncResult(boolean ok,String when,String message){prefs.edit().putString("cloud_last_sync",when==null?"":when).putString("cloud_last_result",message==null?(ok?"Success":"Failed"):message).apply();}
}
