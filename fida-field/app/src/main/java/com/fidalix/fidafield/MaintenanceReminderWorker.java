package com.fidalix.fidafield;

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import androidx.core.content.ContextCompat;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.util.List;

public class MaintenanceReminderWorker extends Worker {
    private static final String CHANNEL="fida_maintenance";
    public MaintenanceReminderWorker(@NonNull Context context,@NonNull WorkerParameters params){super(context,params);}
    @NonNull @Override public Result doWork(){try{send(getApplicationContext());return Result.success();}catch(Exception e){return Result.retry();}}
    public static void notifyNow(Context context){send(context);}
    private static void send(Context context){
        SharedPreferences p=context.getSharedPreferences("fida_field_prefs",Context.MODE_PRIVATE);if(!p.getBoolean("maintenance_notifications",true))return;int days=14;try{days=Integer.parseInt(p.getString("maintenance_reminder_days","14"));}catch(Exception ignored){}days=Math.max(0,Math.min(days,365));AppDatabase db=new AppDatabase(context);List<AppDatabase.Row> due=db.dueAssets(days);if(due.isEmpty())return;int overdue=0;for(AppDatabase.Row a:due)if(!a.s("next_service").isEmpty()&&a.s("next_service").compareTo(db.today())<0)overdue++;if(Build.VERSION.SDK_INT>=26){NotificationManager nm=(NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);nm.createNotificationChannel(new NotificationChannel(CHANNEL,"Maintenance reminders",NotificationManager.IMPORTANCE_DEFAULT));}if(Build.VERSION.SDK_INT>=33&&ContextCompat.checkSelfPermission(context,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)return;Intent open=new Intent(context,MainActivity.class);open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TOP);PendingIntent pi=PendingIntent.getActivity(context,100,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);String title=overdue>0?overdue+" maintenance item"+(overdue==1?"":"s")+" overdue":due.size()+" maintenance item"+(due.size()==1?"":"s")+" due soon";String text=due.get(0).s("name")+" • "+due.get(0).s("next_service")+(due.size()>1?"  +"+(due.size()-1)+" more":"");NotificationCompat.Builder b=new NotificationCompat.Builder(context,CHANNEL).setSmallIcon(R.drawable.ic_assets).setContentTitle(title).setContentText(text).setStyle(new NotificationCompat.BigTextStyle().bigText(text)).setContentIntent(pi).setAutoCancel(true).setPriority(NotificationCompat.PRIORITY_DEFAULT);NotificationManagerCompat.from(context).notify(2201,b.build());
    }
}
