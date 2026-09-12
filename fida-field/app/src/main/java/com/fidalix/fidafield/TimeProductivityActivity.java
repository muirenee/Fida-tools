package com.fidalix.fidafield;

import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class TimeProductivityActivity extends AppCompatActivity {
    private AppDatabase db;
    private AccountTeamManager accountTeam;
    private SharedPreferences prefs;
    private LinearLayout results;
    private Spinner period;
    private Spinner technician;
    private int primary=BrandingManager.DEFAULT_PRIMARY_DARK;
    private int accent=BrandingManager.DEFAULT_ACCENT;

    @Override protected void onCreate(Bundle state){
        super.onCreate(state);
        prefs=getSharedPreferences("fida_field_prefs",MODE_PRIVATE);
        db=new AppDatabase(this);
        accountTeam=new AccountTeamManager(prefs,db);
        buildUi();
    }

    @Override protected void onDestroy(){if(db!=null)db.close();super.onDestroy();}

    private void buildUi(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(0xFFF5F6F4);
        LinearLayout bar=new LinearLayout(this);bar.setGravity(Gravity.CENTER_VERTICAL);bar.setPadding(dp(14),dp(10),dp(14),dp(10));bar.setBackgroundColor(primary);
        MaterialButton back=new MaterialButton(this);back.setText("←");back.setAllCaps(false);back.setTextColor(Color.WHITE);back.setBackgroundColor(Color.TRANSPARENT);back.setOnClickListener(v->finish());bar.addView(back,new LinearLayout.LayoutParams(dp(54),dp(44)));
        LinearLayout titles=new LinearLayout(this);titles.setOrientation(LinearLayout.VERTICAL);TextView title=text("Time & productivity",20,Color.WHITE,true);TextView sub=text("Active service work summary",12,0xFFD6DAD5,false);titles.addView(title);titles.addView(sub);bar.addView(titles,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));root.addView(bar);
        View stripe=new View(this);stripe.setBackgroundColor(accent);root.addView(stripe,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(3)));

        ScrollView scroll=new ScrollView(this);LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(18),dp(18),dp(18),dp(36));scroll.addView(body);root.addView(scroll,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1));
        body.addView(note("Active service time is calculated from Start / Pause / Resume work sessions. Paused time, overnight gaps and waiting periods are excluded."));
        body.addView(label("Period"));period=spinner(new String[]{"Last 7 days","Last 30 days","This year","All dates"});period.setSelection(1);body.addView(period);
        body.addView(label("Technician"));technician=spinner(technicianValues());body.addView(technician);
        results=new LinearLayout(this);results.setOrientation(LinearLayout.VERTICAL);body.addView(results);
        AdapterView.OnItemSelectedListener listener=new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?>p,View v,int pos,long id){render();}public void onNothingSelected(AdapterView<?>p){}};period.setOnItemSelectedListener(listener);technician.setOnItemSelectedListener(listener);
        setContentView(root);render();
    }

    private String[] technicianValues(){
        if(!accountTeam.canManageTeam())return new String[]{"My work"};
        ArrayList<String> out=new ArrayList<>();out.add("All");out.add("Unassigned");for(AppDatabase.Row r:db.technicians())if(!out.contains(r.s("name")))out.add(r.s("name"));return out.toArray(new String[0]);
    }

    private void render(){
        if(results==null)return;results.removeAllViews();long[] range=rangeMillis(String.valueOf(period.getSelectedItem()));long from=range[0],to=range[1],now=System.currentTimeMillis();boolean seeAll=accountTeam.canManageTeam();String techFilter=seeAll?String.valueOf(technician.getSelectedItem()):"All";List<AppDatabase.Row> jobs=db.jobsFilteredScoped("","All","All",techFilter,"","",accountTeam.cloudUserId(),seeAll);
        long totalMs=0;int trackedJobs=0,completed=0,running=0,paused=0;LinkedHashMap<String,Long> byTech=new LinkedHashMap<>();LinkedHashMap<String,Integer> techJobs=new LinkedHashMap<>();ArrayList<JobSummary> recent=new ArrayList<>();
        for(AppDatabase.Row job:jobs){
            JSONArray sessions=db.jobServiceSessions(job.id());long jobMs=0;boolean has=false;
            for(int i=0;i<sessions.length();i++){
                JSONObject s=sessions.optJSONObject(i);if(s==null)continue;long start=s.optLong("started_at_ms",0L),end=s.optLong("ended_at_ms",0L);if(start<=0)continue;if(end<=0)end=now;long a=Math.max(start,from),b=Math.min(end,to);if(b<=a)continue;jobMs+=b-a;has=true;
            }
            if(!has)continue;trackedJobs++;totalMs+=jobMs;String who=job.s("technician").trim();if(who.isEmpty())who="Unassigned";byTech.put(who,byTech.getOrDefault(who,0L)+jobMs);techJobs.put(who,techJobs.getOrDefault(who,0)+1);
            long finished=job.l("service_completed_at_ms");if("Completed".equalsIgnoreCase(job.s("status"))&&finished>0&&finished>=from&&finished<to)completed++;
            if(!"Completed".equalsIgnoreCase(job.s("status"))&&!"Cancelled".equalsIgnoreCase(job.s("status"))){if(db.jobServiceRunning(job.id()))running++;else paused++;}
            if(recent.size()<12)recent.add(new JobSummary(job.s("report_no")+" · "+job.s("title"),who,job.s("status"),jobMs));
        }
        results.addView(section("Summary"));LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.addView(stat("Active time",formatMs(totalMs)),new LinearLayout.LayoutParams(0,dp(104),1));stats.addView(space());stats.addView(stat("Tracked jobs",String.valueOf(trackedJobs)),new LinearLayout.LayoutParams(0,dp(104),1));results.addView(stats);
        results.addView(info("Completed in period",String.valueOf(completed)));results.addView(info("Running / paused now",running+" / "+paused));results.addView(info("Average active time / tracked job",trackedJobs==0?"0 min":formatMs(totalMs/trackedJobs)));
        results.addView(section("Technician totals"));if(byTech.isEmpty())results.addView(note("No tracked service sessions in this period."));else for(Map.Entry<String,Long> e:byTech.entrySet())results.addView(card(e.getKey(),techJobs.getOrDefault(e.getKey(),0)+" tracked job(s)",formatMs(e.getValue())));
        results.addView(section("Recent timed jobs"));if(recent.isEmpty())results.addView(note("No timed jobs in this period."));else for(JobSummary j:recent)results.addView(card(j.title,j.technician+" · "+j.status,formatMs(j.millis)));
        if(!seeAll)results.addView(note("This account shows only jobs assigned to your field-person profile."));
    }

    private long[] rangeMillis(String preset){
        Calendar end=Calendar.getInstance();end.set(Calendar.HOUR_OF_DAY,0);end.set(Calendar.MINUTE,0);end.set(Calendar.SECOND,0);end.set(Calendar.MILLISECOND,0);end.add(Calendar.DAY_OF_YEAR,1);Calendar start=(Calendar)end.clone();
        if("Last 7 days".equals(preset))start.add(Calendar.DAY_OF_YEAR,-7);else if("Last 30 days".equals(preset))start.add(Calendar.DAY_OF_YEAR,-30);else if("This year".equals(preset)){start.set(Calendar.MONTH,Calendar.JANUARY);start.set(Calendar.DAY_OF_MONTH,1);start.set(Calendar.HOUR_OF_DAY,0);start.set(Calendar.MINUTE,0);start.set(Calendar.SECOND,0);start.set(Calendar.MILLISECOND,0);}else return new long[]{0L,Long.MAX_VALUE};return new long[]{start.getTimeInMillis(),end.getTimeInMillis()};
    }

    private String formatMs(long ms){if(ms<=0)return "0 min";long minutes=ms/60000L;if(minutes<1)return "< 1 min";long days=minutes/1440,h=(minutes%1440)/60,m=minutes%60;StringBuilder s=new StringBuilder();if(days>0)s.append(days).append(" d ");if(h>0)s.append(h).append(" h ");if(m>0||s.length()==0)s.append(m).append(" min");return s.toString().trim();}
    private Spinner spinner(String[] values){Spinner s=new Spinner(this);ArrayAdapter<String>a=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,values);a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);s.setAdapter(a);s.setBackgroundColor(Color.WHITE);s.setPadding(dp(10),0,dp(10),0);return s;}
    private TextView label(String value){TextView t=text(value.toUpperCase(Locale.US),10,0xFF70756F,true);t.setPadding(0,dp(14),0,dp(5));return t;}
    private TextView section(String value){TextView t=text(value,16,0xFF2D312D,true);t.setPadding(0,dp(24),0,dp(8));return t;}
    private TextView note(String value){TextView t=text(value,13,0xFF70756F,false);t.setPadding(dp(12),dp(12),dp(12),dp(12));t.setBackgroundColor(0xFFF0F2EF);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(0,dp(6),0,dp(6));t.setLayoutParams(p);return t;}
    private View info(String name,String value){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(0,dp(5),0,dp(7));l.addView(text(name.toUpperCase(Locale.US),10,0xFF70756F,true));l.addView(text(value,15,0xFF2D312D,false));return l;}
    private MaterialCardView stat(String name,String value){MaterialCardView c=new MaterialCardView(this);c.setRadius(dp(18));c.setCardBackgroundColor(Color.WHITE);c.setStrokeColor(0xFFE1E4E0);c.setStrokeWidth(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(14),dp(12),dp(14),dp(12));l.addView(text(name,11,0xFF70756F,false));l.addView(text(value,22,0xFF2D312D,true));c.addView(l);return c;}
    private MaterialCardView card(String title,String meta,String badge){MaterialCardView c=new MaterialCardView(this);c.setRadius(dp(16));c.setCardBackgroundColor(Color.WHITE);c.setStrokeColor(0xFFE1E4E0);c.setStrokeWidth(dp(1));LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(14),dp(12),dp(14),dp(12));LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(text(title,14,0xFF2D312D,true));copy.addView(text(meta,11,0xFF70756F,false));row.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));TextView b=text(badge,11,accent,true);b.setPadding(dp(8),dp(5),dp(8),dp(5));row.addView(b);c.addView(row);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(0,dp(5),0,dp(5));c.setLayoutParams(p);return c;}
    private TextView text(String value,float size,int color,boolean bold){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setTextColor(color);if(bold)t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);return t;}
    private View space(){View v=new View(this);v.setLayoutParams(new LinearLayout.LayoutParams(dp(10),1));return v;}
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private static class JobSummary{final String title,technician,status;final long millis;JobSummary(String t,String tech,String s,long m){title=t;technician=tech;status=s;millis=m;}}
}
