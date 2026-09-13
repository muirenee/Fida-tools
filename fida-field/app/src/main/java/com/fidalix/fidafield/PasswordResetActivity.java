package com.fidalix.fidafield;

import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.button.MaterialButton;

/** Handles the Supabase password-recovery deep link and lets the user choose a new password. */
public class PasswordResetActivity extends AppCompatActivity {
    private SharedPreferences prefs;
    private SupabaseClientLite client;
    private LinearLayout body;

    @Override protected void onCreate(Bundle savedInstanceState){
        super.onCreate(savedInstanceState);
        prefs=getSharedPreferences("fida_field_prefs",MODE_PRIVATE);client=new SupabaseClientLite(prefs);buildScreen();handleRecoveryIntent(getIntent());
    }

    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);handleRecoveryIntent(intent);}

    private void buildScreen(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(0xFFF5F6F4);
        TextView header=new TextView(this);header.setText("Fida Field");header.setTextColor(Color.WHITE);header.setTextSize(22);header.setGravity(Gravity.CENTER_VERTICAL);header.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);header.setPadding(dp(22),dp(18),dp(22),dp(18));header.setBackgroundColor(BrandingManager.DEFAULT_PRIMARY_DARK);root.addView(header,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT));
        ViewGroup.LayoutParams lp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(3));TextView accent=new TextView(this);accent.setBackgroundColor(BrandingManager.DEFAULT_ACCENT);root.addView(accent,lp);
        ScrollView scroll=new ScrollView(this);body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(20),dp(24),dp(20),dp(32));scroll.addView(body);root.addView(scroll,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1));setContentView(root);
    }

    private void handleRecoveryIntent(Intent intent){
        body.removeAllViews();Uri uri=intent==null?null:intent.getData();String error=param(uri,"error_description");if(error.isEmpty())error=param(uri,"error");String type=param(uri,"type"),access=param(uri,"access_token"),refresh=param(uri,"refresh_token");long expires=parseLong(param(uri,"expires_in"),3600L);
        if(!error.isEmpty()){showInvalid("The reset link could not be used: "+error);return;}
        if(uri==null||!"fidafield".equalsIgnoreCase(uri.getScheme())||!"password-reset".equalsIgnoreCase(uri.getHost())||(!type.isEmpty()&&!"recovery".equalsIgnoreCase(type))||access.isEmpty()){showInvalid("This password-reset link is invalid or has expired. Request a new link from Account & workspace.");return;}
        try{client.adoptRecoverySession(access,refresh,expires);showPasswordForm();}catch(Exception e){showInvalid(e.getMessage());}
    }

    private void showPasswordForm(){
        body.addView(title("Choose a new password"));body.addView(text("Your reset link has been verified. Enter a new password for this account."));
        EditText password=field("New password");password.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);EditText confirm=field("Confirm new password");confirm.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);body.addView(password);body.addView(confirm);
        TextView hint=text("Use at least 8 characters. Your workspace, jobs, history and permissions will stay unchanged.");hint.setTextSize(12);body.addView(hint);
        MaterialButton save=primary("Update password");body.addView(save);MaterialButton cancel=secondary("Cancel recovery");body.addView(cancel);
        save.setOnClickListener(v->{String p=value(password),c=value(confirm);if(p.length()<8){password.setError("Use at least 8 characters");return;}if(!p.equals(c)){confirm.setError("Passwords do not match");return;}save.setEnabled(false);save.setText("Updating…");new Thread(()->{try{SupabaseClientLite.AuthResult ar=client.updatePassword(p);try{AppDatabase db=new AppDatabase(this);AccountTeamManager team=new AccountTeamManager(prefs,db);String name=team.accountName();if(name==null||name.trim().isEmpty())name=ar.email;team.bindCloudAccount(ar.userId,name,ar.email);CloudSyncFoundation cloud=new CloudSyncFoundation(this,prefs,db);CloudSyncFoundation.WorkspaceMembership wm=cloud.firstWorkspace();if(wm!=null)team.bindCloudWorkspace(wm.id,wm.name,wm.role);db.close();}catch(Exception ignored){}runOnUiThread(this::showSuccess);}catch(Exception e){runOnUiThread(()->{save.setEnabled(true);save.setText("Update password");showError(e.getMessage());});}}).start();});
        cancel.setOnClickListener(v->{client.clearSession();openFidaField();});
    }

    private void showSuccess(){body.removeAllViews();body.addView(title("Password updated"));body.addView(text("Your password has been changed successfully. You can continue using Fida Field with the same account and workspace."));MaterialButton go=primary("Continue to Fida Field");go.setOnClickListener(v->openFidaField());body.addView(go);}
    private void showInvalid(String message){body.addView(title("Password reset"));body.addView(text(message));MaterialButton back=primary("Back to Fida Field");back.setOnClickListener(v->openFidaField());body.addView(back);}
    private void showError(String message){new com.google.android.material.dialog.MaterialAlertDialogBuilder(this).setTitle("Could not update password").setMessage(message==null||message.trim().isEmpty()?"Please request a new reset link and try again.":message).setPositiveButton("OK",null).show();}
    private void openFidaField(){Intent i=new Intent(this,FidaFieldActivity.class);i.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_NEW_TASK);startActivity(i);finish();}

    private String param(Uri uri,String name){if(uri==null)return "";String q=uri.getQueryParameter(name);if(q!=null&&!q.isEmpty())return q;String f=uri.getFragment();if(f==null||f.isEmpty())return "";try{Uri x=Uri.parse("https://local/?"+f);String v=x.getQueryParameter(name);return v==null?"":v;}catch(Exception e){return "";}}
    private long parseLong(String value,long fallback){try{return Long.parseLong(value);}catch(Exception e){return fallback;}}
    private String value(EditText e){return e.getText()==null?"":e.getText().toString().trim();}
    private TextView title(String s){TextView v=new TextView(this);v.setText(s);v.setTextSize(24);v.setTextColor(0xFF2D312D);v.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);v.setPadding(0,0,0,dp(10));return v;}
    private TextView text(String s){TextView v=new TextView(this);v.setText(s);v.setTextSize(15);v.setTextColor(0xFF60665F);v.setLineSpacing(0,1.15f);v.setPadding(0,0,0,dp(16));return v;}
    private EditText field(String hint){EditText e=new EditText(this);e.setHint(hint);e.setTextSize(15);e.setSingleLine(true);e.setPadding(dp(16),dp(12),dp(16),dp(12));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(58));p.setMargins(0,dp(6),0,dp(6));e.setLayoutParams(p);return e;}
    private MaterialButton primary(String label){MaterialButton b=new MaterialButton(this);b.setText(label);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(12),0,dp(6));b.setLayoutParams(p);return b;}
    private MaterialButton secondary(String label){MaterialButton b=new MaterialButton(this,null,com.google.android.material.R.attr.materialButtonOutlinedStyle);b.setText(label);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(6),0,dp(6));b.setLayoutParams(p);return b;}
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
}
