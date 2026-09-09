package com.fidalix.fidafield;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.util.concurrent.TimeUnit;

/** Network-constrained background synchronization. Manual Sync Now remains available. */
public class CloudSyncWorker extends Worker {
    public static final String KEY_ENABLED="cloud_auto_sync";
    public static final String KEY_LAST_RUN="cloud_background_last_run";
    public static final String KEY_LAST_RESULT="cloud_background_last_result";
    private static final String PERIODIC="fida-cloud-sync-periodic";
    private static final String IMMEDIATE="fida-cloud-sync-immediate";

    public CloudSyncWorker(@NonNull Context context,@NonNull WorkerParameters params){super(context,params);}

    public static void configure(Context context,boolean enabled){
        WorkManager wm=WorkManager.getInstance(context);
        if(!enabled){wm.cancelUniqueWork(PERIODIC);wm.cancelUniqueWork(IMMEDIATE);return;}
        Constraints network=new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
        PeriodicWorkRequest periodic=new PeriodicWorkRequest.Builder(CloudSyncWorker.class,15,TimeUnit.MINUTES).setConstraints(network).build();
        wm.enqueueUniquePeriodicWork(PERIODIC, ExistingPeriodicWorkPolicy.UPDATE,periodic);
        OneTimeWorkRequest immediate=new OneTimeWorkRequest.Builder(CloudSyncWorker.class).setConstraints(network).build();
        wm.enqueueUniqueWork(IMMEDIATE, ExistingWorkPolicy.REPLACE,immediate);
    }

    @NonNull @Override public Result doWork(){
        Context c=getApplicationContext();SharedPreferences prefs=c.getSharedPreferences("fida_field_prefs",Context.MODE_PRIVATE);
        if(!prefs.getBoolean(KEY_ENABLED,true))return Result.success();
        AppDatabase db=new AppDatabase(c);AccountTeamManager team=new AccountTeamManager(prefs,db);CloudSyncFoundation cloud=new CloudSyncFoundation(c,prefs,db);
        if(!cloud.backendConfigured()||!cloud.signedIn()||!team.hasCloudWorkspace()){db.close();return Result.success();}
        try{
            CloudSyncFoundation.SyncResult r=cloud.syncNow(team.workspaceId(),team.canManageTeam());
            String when=db.now();prefs.edit().putString(KEY_LAST_RUN,when).putString(KEY_LAST_RESULT,r.message).apply();return Result.success();
        }catch(Exception e){
            String msg=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();prefs.edit().putString(KEY_LAST_RUN,db.now()).putString(KEY_LAST_RESULT,"Failed · "+msg).apply();
            return getRunAttemptCount()<4?Result.retry():Result.success();
        }finally{db.close();}
    }
}
