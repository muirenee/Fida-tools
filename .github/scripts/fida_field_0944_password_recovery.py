from pathlib import Path

GRADLE = Path('fida-field/app/build.gradle')
CLIENT = Path('fida-field/app/src/main/java/com/fidalix/fidafield/SupabaseClientLite.java')
CLOUD = Path('fida-field/app/src/main/java/com/fidalix/fidafield/CloudSyncFoundation.java')
MAIN = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
MANIFEST = Path('fida-field/app/src/main/AndroidManifest.xml')
RESET = Path('fida-field/app/src/main/java/com/fidalix/fidafield/PasswordResetActivity.java')


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected source fragment not found in {path}: {old[:180]!r}')
    path.write_text(text.replace(old, new, 1))

replace_once(
    GRADLE,
    "versionCode 46\n        versionName '0.9.43-test'",
    "versionCode 47\n        versionName '0.9.44-test'",
)

# Native Supabase password-recovery primitives. The recovery email redirects back into the app.
replace_once(
    CLIENT,
    '''    public AuthResult signIn(String email,String password)throws Exception{\n        JSONObject body=new JSONObject().put("email",email.trim()).put("password",password);\n        Object raw=request("POST",BuildConfig.SUPABASE_URL+"/auth/v1/token?grant_type=password",body,false,null,null);\n        JSONObject o=(JSONObject)raw;saveSession(o);JSONObject user=o.optJSONObject("user");\n        return new AuthResult(true,false,user==null?userId():user.optString("id",userId()),user==null?email.trim():user.optString("email",email.trim()));\n    }\n\n''',
    '''    public AuthResult signIn(String email,String password)throws Exception{\n        JSONObject body=new JSONObject().put("email",email.trim()).put("password",password);\n        Object raw=request("POST",BuildConfig.SUPABASE_URL+"/auth/v1/token?grant_type=password",body,false,null,null);\n        JSONObject o=(JSONObject)raw;saveSession(o);JSONObject user=o.optJSONObject("user");\n        return new AuthResult(true,false,user==null?userId():user.optString("id",userId()),user==null?email.trim():user.optString("email",email.trim()));\n    }\n\n    public void requestPasswordReset(String email)throws Exception{\n        String redirect="fidafield://password-reset";\n        JSONObject body=new JSONObject().put("email",email==null?"":email.trim());\n        request("POST",BuildConfig.SUPABASE_URL+"/auth/v1/recover?redirect_to="+enc(redirect),body,false,null,null);\n    }\n\n    public void adoptRecoverySession(String accessToken,String refreshToken,long expiresIn)throws Exception{\n        String access=accessToken==null?"":accessToken.trim();if(access.isEmpty())throw new Exception("Password reset link did not contain a recovery session");\n        String refresh=refreshToken==null?"":refreshToken.trim();long seconds=expiresIn>0?expiresIn:3600L;\n        prefs.edit().putString(KEY_ACCESS,access).putString(KEY_REFRESH,refresh).putLong(KEY_EXPIRES,System.currentTimeMillis()/1000L+Math.max(60L,seconds)).apply();\n    }\n\n    public AuthResult updatePassword(String password)throws Exception{\n        if(password==null||password.length()<8)throw new Exception("Use at least 8 characters");\n        Object raw=request("PUT",BuildConfig.SUPABASE_URL+"/auth/v1/user",new JSONObject().put("password",password),true,null,null);\n        JSONObject user=raw instanceof JSONObject?(JSONObject)raw:new JSONObject();String uid=user.optString("id",userId()),email=user.optString("email",accountEmail());\n        prefs.edit().putString(KEY_USER_ID,uid).putString(KEY_EMAIL,email).apply();\n        return new AuthResult(true,false,uid,email);\n    }\n\n'''
)

replace_once(
    CLOUD,
    '    public SupabaseClientLite.AuthResult signIn(String email,String password)throws Exception{return client.signIn(email,password);}\n',
    '    public SupabaseClientLite.AuthResult signIn(String email,String password)throws Exception{return client.signIn(email,password);}\n    public void requestPasswordReset(String email)throws Exception{client.requestPasswordReset(email);}\n'
)

# Forgot-password action on both ordinary sign-in and invited-user sign-in.
replace_once(
    MAIN,
    '        b.addView(signIn);\n        b.addView(paragraph("Fallback: if the email button did not open Fida Field, you can still sign in normally and use the invitation code shown in the email."));',
    '        b.addView(signIn);\n        MaterialButton forgotInvite=outlineButton("Forgot password?");forgotInvite.setOnClickListener(v->showForgotPassword(val(email)));b.addView(forgotInvite);\n        b.addView(paragraph("Fallback: if the email button did not open Fida Field, you can still sign in normally and use the invitation code shown in the email."));'
)

replace_once(
    MAIN,
    '            b.addView(paragraph("Fida Field remains fully usable offline without signing in. Cloud sign-in is required only for multi-device synchronization and team workspaces."));return;',
    '            MaterialButton forgot=outlineButton("Forgot password?");forgot.setOnClickListener(v->showForgotPassword(val(cloudEmail)));b.addView(forgot);\n            b.addView(paragraph("Fida Field remains fully usable offline without signing in. Cloud sign-in is required only for multi-device synchronization and team workspaces."));return;'
)

replace_once(
    MAIN,
    '    private void acceptPendingInviteNow(String displayName){',
    '''    private void showForgotPassword(String suggestedEmail){\n        LinearLayout f=form();f.addView(paragraph("Enter the email address used for your Fida Field account. We will send a secure password-reset link."));EditText email=input("Account email",suggestedEmail==null?"":suggestedEmail);f.addView(email);\n        AlertDialog d=new MaterialAlertDialogBuilder(this).setTitle("Reset password").setView(scrollForm(f)).setNegativeButton("Cancel",null).setPositiveButton("Send reset link",null).create();d.setCanceledOnTouchOutside(false);\n        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{String e=val(email);if(e.isEmpty()||!android.util.Patterns.EMAIL_ADDRESS.matcher(e).matches()){email.setError("Enter a valid email");return;}runCloud("Sending password reset email…",()->{cloudSync.requestPasswordReset(e);return null;},obj->{d.dismiss();new MaterialAlertDialogBuilder(this).setTitle("Check your email").setMessage("If an account exists for "+e+", a password-reset email has been sent. Open the link on this Android device to choose a new password in Fida Field.").setPositiveButton("OK",null).show();});}));d.show();\n    }\n\n    private void acceptPendingInviteNow(String displayName){'''
)

# Dedicated activity receives the Supabase recovery redirect.
replace_once(
    MANIFEST,
    '        <activity android:name=".TimeProductivityActivity" android:exported="false" />\n        <activity android:name=".MainActivity" android:exported="false" />',
    '''        <activity android:name=".TimeProductivityActivity" android:exported="false" />\n        <activity android:name=".MainActivity" android:exported="false" />\n        <activity android:name=".PasswordResetActivity" android:exported="true">\n            <intent-filter>\n                <action android:name="android.intent.action.VIEW" />\n                <category android:name="android.intent.category.DEFAULT" />\n                <category android:name="android.intent.category.BROWSABLE" />\n                <data android:scheme="fidafield" android:host="password-reset" />\n            </intent-filter>\n        </activity>'''
)

RESET.write_text(r'''package com.fidalix.fidafield;

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
import com.google.android.material.card.MaterialCardView;

import org.json.JSONObject;

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
        save.setOnClickListener(v->{String p=value(password),c=value(confirm);if(p.length()<8){password.setError("Use at least 8 characters");return;}if(!p.equals(c)){confirm.setError("Passwords do not match");return;}save.setEnabled(false);save.setText("Updating…");new Thread(()->{try{SupabaseClientLite.AuthResult ar=client.updatePassword(p);try{AppDatabase db=new AppDatabase(this);AccountTeamManager team=new AccountTeamManager(prefs,db);String name=team.accountName();if(name==null||name.trim().isEmpty())name=ar.email;team.bindCloudAccount(ar.userId,name,ar.email);CloudSyncFoundation cloud=new CloudSyncFoundation(this,prefs,db);CloudSyncFoundation.WorkspaceMembership wm=cloud.firstWorkspace();if(wm!=null)team.bindCloudWorkspace(wm.id,wm.name,wm.role);}catch(Exception ignored){}runOnUiThread(()->showSuccess());}catch(Exception e){runOnUiThread(()->{save.setEnabled(true);save.setText("Update password");showError(e.getMessage());});}}).start();});
        cancel.setOnClickListener(v->{client.clearSession();openFidaField();});
    }

    private void showSuccess(){body.removeAllViews();body.addView(title("Password updated"));body.addView(text("Your password has been changed successfully. You can continue using Fida Field with the same account and workspace."));MaterialButton go=primary("Continue to Fida Field");go.setOnClickListener(v->openFidaField());body.addView(go);}
    private void showInvalid(String message){body.addView(title("Password reset"));body.addView(text(message));MaterialButton back=primary("Back to Fida Field");back.setOnClickListener(v->openFidaField());body.addView(back);}
    private void showError(String message){new com.google.android.material.dialog.MaterialAlertDialogBuilder(this).setTitle("Could not update password").setMessage(message==null||message.trim().isEmpty()?"Please request a new reset link and try again.":message).setPositiveButton("OK",null).show();}
    private void openFidaField(){Intent i=new Intent(this,FidaFieldActivity.class);i.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_NEW_TASK);startActivity(i);finish();}

    private String param(Uri uri,String name){if(uri==null)return "";String q=uri.getQueryParameter(name);if(q!=null&&!q.isEmpty())return q;String f=uri.getFragment();if(f==null||f.isEmpty())return "";try{return Uri.parse("https://local/?"+f).getQueryParameter(name)==null?"":Uri.parse("https://local/?"+f).getQueryParameter(name);}catch(Exception e){return "";}}
    private long parseLong(String value,long fallback){try{return Long.parseLong(value);}catch(Exception e){return fallback;}}
    private String value(EditText e){return e.getText()==null?"":e.getText().toString().trim();}
    private TextView title(String s){TextView v=new TextView(this);v.setText(s);v.setTextSize(24);v.setTextColor(0xFF2D312D);v.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);v.setPadding(0,0,0,dp(10));return v;}
    private TextView text(String s){TextView v=new TextView(this);v.setText(s);v.setTextSize(15);v.setTextColor(0xFF60665F);v.setLineSpacing(0,1.15f);v.setPadding(0,0,0,dp(16));return v;}
    private EditText field(String hint){EditText e=new EditText(this);e.setHint(hint);e.setTextSize(15);e.setSingleLine(true);e.setPadding(dp(16),dp(12),dp(16),dp(12));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(58));p.setMargins(0,dp(6),0,dp(6));e.setLayoutParams(p);return e;}
    private MaterialButton primary(String label){MaterialButton b=new MaterialButton(this);b.setText(label);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(12),0,dp(6));b.setLayoutParams(p);return b;}
    private MaterialButton secondary(String label){MaterialButton b=new MaterialButton(this,null,com.google.android.material.R.attr.materialButtonOutlinedStyle);b.setText(label);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(6),0,dp(6));b.setLayoutParams(p);return b;}
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
}
''')

print('Fida Field 0.9.44 password recovery patch applied')
