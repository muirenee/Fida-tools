package com.fidalix.fidafield;

import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** Minimal Supabase Auth/PostgREST/Storage client used by the native Java app.
 * It intentionally keeps the publishable key client-side and relies on Supabase Auth + RLS
 * for authorization. No service-role/secret key is ever shipped in the APK. */
public class SupabaseClientLite {
    private static final String KEY_ACCESS="cloud_access_token";
    private static final String KEY_REFRESH="cloud_refresh_token";
    private static final String KEY_EXPIRES="cloud_access_expires_at";
    private static final String KEY_EMAIL="cloud_account_email";
    private static final String KEY_USER_ID="cloud_user_id";

    public static class AuthResult {
        public final boolean signedIn;
        public final boolean emailConfirmationRequired;
        public final String userId;
        public final String email;
        public AuthResult(boolean signedIn,boolean emailConfirmationRequired,String userId,String email){
            this.signedIn=signedIn;this.emailConfirmationRequired=emailConfirmationRequired;this.userId=userId;this.email=email;
        }
    }

    private final SharedPreferences prefs;
    public SupabaseClientLite(SharedPreferences prefs){this.prefs=prefs;}

    public boolean configured(){return !BuildConfig.SUPABASE_URL.trim().isEmpty()&&!BuildConfig.SUPABASE_PUBLISHABLE_KEY.trim().isEmpty();}
    public boolean hasStoredSession(){return configured()&&!prefs.getString(KEY_REFRESH,"").isEmpty();}
    public String accountEmail(){return prefs.getString(KEY_EMAIL,"");}
    public String userId(){return prefs.getString(KEY_USER_ID,"");}

    public AuthResult signUp(String name,String email,String password)throws Exception{
        JSONObject body=new JSONObject().put("email",email.trim()).put("password",password);
        if(name!=null&&!name.trim().isEmpty())body.put("data",new JSONObject().put("full_name",name.trim()));
        Object raw=request("POST",BuildConfig.SUPABASE_URL+"/auth/v1/signup",body,false,null,null);
        JSONObject o=raw instanceof JSONObject?(JSONObject)raw:new JSONObject();
        JSONObject user=o.optJSONObject("user");String uid=user==null?"":user.optString("id","");String actualEmail=user==null?email.trim():user.optString("email",email.trim());
        boolean signed=!o.optString("access_token","").isEmpty();
        if(signed)saveSession(o);else prefs.edit().putString(KEY_EMAIL,actualEmail).putString(KEY_USER_ID,uid).apply();
        return new AuthResult(signed,!signed,uid,actualEmail);
    }

    public AuthResult signIn(String email,String password)throws Exception{
        JSONObject body=new JSONObject().put("email",email.trim()).put("password",password);
        Object raw=request("POST",BuildConfig.SUPABASE_URL+"/auth/v1/token?grant_type=password",body,false,null,null);
        JSONObject o=(JSONObject)raw;saveSession(o);JSONObject user=o.optJSONObject("user");
        return new AuthResult(true,false,user==null?userId():user.optString("id",userId()),user==null?email.trim():user.optString("email",email.trim()));
    }

    public void signOut()throws Exception{
        String token=accessToken();
        if(!token.isEmpty())request("POST",BuildConfig.SUPABASE_URL+"/auth/v1/logout",new JSONObject(),true,null,null);
        clearSession();
    }

    public JSONObject currentUser()throws Exception{
        Object raw=request("GET",BuildConfig.SUPABASE_URL+"/auth/v1/user",null,true,null,null);
        return raw instanceof JSONObject?(JSONObject)raw:new JSONObject();
    }

    public Object rpc(String function,JSONObject body)throws Exception{
        return request("POST",BuildConfig.SUPABASE_URL+"/rest/v1/rpc/"+function,body==null?new JSONObject():body,true,"Prefer","return=representation");
    }

    public JSONArray select(String table,String query)throws Exception{
        String url=BuildConfig.SUPABASE_URL+"/rest/v1/"+table+(query==null||query.isEmpty()?"":"?"+query);
        Object raw=request("GET",url,null,true,null,null);
        if(raw instanceof JSONArray)return (JSONArray)raw;
        JSONArray a=new JSONArray();if(raw instanceof JSONObject)a.put(raw);return a;
    }

    public JSONArray upsert(String table,String conflict,JSONObject body)throws Exception{
        String q=conflict==null||conflict.isEmpty()?"":"?on_conflict="+enc(conflict);
        Object raw=request("POST",BuildConfig.SUPABASE_URL+"/rest/v1/"+table+q,body,true,"Prefer","resolution=merge-duplicates,return=representation");
        if(raw instanceof JSONArray)return (JSONArray)raw;JSONArray a=new JSONArray();if(raw instanceof JSONObject)a.put(raw);return a;
    }

    public void update(String table,String filter,JSONObject body)throws Exception{
        request("PATCH",BuildConfig.SUPABASE_URL+"/rest/v1/"+table+"?"+filter,body,true,"Prefer","return=minimal");
    }

    public Object invokeFunction(String function,JSONObject body)throws Exception{
        String name=function==null?"":function.trim();if(name.isEmpty())throw new Exception("Missing Edge Function name");
        return request("POST",BuildConfig.SUPABASE_URL+"/functions/v1/"+enc(name),body==null?new JSONObject():body,true,null,null);
    }

    public Object invokePublicFunction(String function,JSONObject body)throws Exception{
        String name=function==null?"":function.trim();if(name.isEmpty())throw new Exception("Missing Edge Function name");
        return request("POST",BuildConfig.SUPABASE_URL+"/functions/v1/"+enc(name),body==null?new JSONObject():body,false,null,null);
    }

    /** Standard Supabase Storage upload. x-upsert makes retries idempotent. */
    public void uploadObject(String bucket,String path,byte[] bytes,String contentType)throws Exception{
        if(bytes==null)throw new Exception("No file data to upload");
        String address=BuildConfig.SUPABASE_URL+"/storage/v1/object/"+pathEncode(bucket)+"/"+pathEncode(path);
        HttpURLConnection c=authorizedConnection("POST",address);c.setDoOutput(true);c.setRequestProperty("Content-Type",contentType==null||contentType.isEmpty()?"application/octet-stream":contentType);c.setRequestProperty("x-upsert","true");c.setFixedLengthStreamingMode(bytes.length);
        try(OutputStream out=c.getOutputStream()){out.write(bytes);}int code=c.getResponseCode();InputStream stream=code>=200&&code<300?c.getInputStream():c.getErrorStream();String text=read(stream);if(code<200||code>=300)throw new Exception(errorMessage(text,"Storage upload failed ("+code+")"));
    }

    /** Downloads from the authenticated/private Storage route. */
    public byte[] downloadObject(String bucket,String path)throws Exception{
        String address=BuildConfig.SUPABASE_URL+"/storage/v1/object/authenticated/"+pathEncode(bucket)+"/"+pathEncode(path);
        HttpURLConnection c=authorizedConnection("GET",address);int code=c.getResponseCode();InputStream stream=code>=200&&code<300?c.getInputStream():c.getErrorStream();
        if(code<200||code>=300){String text=read(stream);throw new Exception(errorMessage(text,"Storage download failed ("+code+")"));}
        return readBytes(stream);
    }

    public void deleteObject(String bucket,String path)throws Exception{
        if(path==null||path.trim().isEmpty())return;String address=BuildConfig.SUPABASE_URL+"/storage/v1/object/"+pathEncode(bucket)+"/"+pathEncode(path);HttpURLConnection c=authorizedConnection("DELETE",address);int code=c.getResponseCode();InputStream stream=code>=200&&code<300?c.getInputStream():c.getErrorStream();String text=read(stream);if(code<200||code>=300)throw new Exception(errorMessage(text,"Storage delete failed ("+code+")"));
    }

    public String accessToken()throws Exception{
        if(!configured())return "";
        String token=prefs.getString(KEY_ACCESS,"");long expiry=prefs.getLong(KEY_EXPIRES,0L);long now=System.currentTimeMillis()/1000L;
        if(!token.isEmpty()&&expiry>now+60)return token;
        String refresh=prefs.getString(KEY_REFRESH,"");if(refresh.isEmpty())return token;
        JSONObject body=new JSONObject().put("refresh_token",refresh);
        Object raw=request("POST",BuildConfig.SUPABASE_URL+"/auth/v1/token?grant_type=refresh_token",body,false,null,null);
        if(raw instanceof JSONObject){saveSession((JSONObject)raw);return prefs.getString(KEY_ACCESS,"");}
        return token;
    }

    private void saveSession(JSONObject o){
        String access=o.optString("access_token","");String refresh=o.optString("refresh_token",prefs.getString(KEY_REFRESH,""));long expires=o.optLong("expires_in",3600);JSONObject user=o.optJSONObject("user");
        SharedPreferences.Editor e=prefs.edit().putString(KEY_ACCESS,access).putString(KEY_REFRESH,refresh).putLong(KEY_EXPIRES,System.currentTimeMillis()/1000L+Math.max(60,expires));
        if(user!=null){e.putString(KEY_EMAIL,user.optString("email",prefs.getString(KEY_EMAIL,"")));e.putString(KEY_USER_ID,user.optString("id",prefs.getString(KEY_USER_ID,"")));}e.apply();
    }

    public void clearSession(){prefs.edit().remove(KEY_ACCESS).remove(KEY_REFRESH).remove(KEY_EXPIRES).remove(KEY_EMAIL).remove(KEY_USER_ID).apply();}

    private HttpURLConnection authorizedConnection(String method,String address)throws Exception{
        if(!configured())throw new Exception("Supabase is not configured in this build");String token=accessToken();if(token.isEmpty())throw new Exception("Please sign in first");HttpURLConnection c=(HttpURLConnection)new URL(address).openConnection();c.setRequestMethod(method);c.setConnectTimeout(20000);c.setReadTimeout(60000);c.setRequestProperty("apikey",BuildConfig.SUPABASE_PUBLISHABLE_KEY);c.setRequestProperty("Authorization","Bearer "+token);c.setRequestProperty("Accept","application/json");return c;
    }

    private Object request(String method,String address,JSONObject body,boolean authenticated,String extraHeader,String extraValue)throws Exception{
        if(!configured())throw new Exception("Supabase is not configured in this build");
        HttpURLConnection c=(HttpURLConnection)new URL(address).openConnection();c.setRequestMethod(method);c.setConnectTimeout(15000);c.setReadTimeout(30000);c.setRequestProperty("apikey",BuildConfig.SUPABASE_PUBLISHABLE_KEY);c.setRequestProperty("Accept","application/json");
        if(authenticated){String token=accessToken();if(token.isEmpty())throw new Exception("Please sign in first");c.setRequestProperty("Authorization","Bearer "+token);}
        if(extraHeader!=null)c.setRequestProperty(extraHeader,extraValue);
        if(body!=null&&!("GET".equals(method))){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");byte[] bytes=body.toString().getBytes(StandardCharsets.UTF_8);try(OutputStream out=c.getOutputStream()){out.write(bytes);}}
        int code=c.getResponseCode();InputStream stream=code>=200&&code<300?c.getInputStream():c.getErrorStream();String text=read(stream);
        if(code<200||code>=300)throw new Exception(errorMessage(text,"Supabase request failed ("+code+")"));
        if(text==null||text.trim().isEmpty())return null;return new JSONTokener(text).nextValue();
    }

    private String errorMessage(String text,String fallback){
        try{Object v=new JSONTokener(text).nextValue();if(v instanceof JSONObject){JSONObject o=(JSONObject)v;String m=o.optString("msg",o.optString("message",o.optString("error_description",o.optString("error",fallback))));return m.isEmpty()?fallback:m;}}catch(Exception ignored){}return text==null||text.trim().isEmpty()?fallback:text.trim();
    }
    private String read(InputStream in)throws Exception{if(in==null)return "";StringBuilder b=new StringBuilder();try(BufferedReader r=new BufferedReader(new InputStreamReader(in,StandardCharsets.UTF_8))){String line;while((line=r.readLine())!=null)b.append(line);}return b.toString();}
    private byte[] readBytes(InputStream in)throws Exception{if(in==null)return new byte[0];try(InputStream src=in;ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] buf=new byte[16384];int n;while((n=src.read(buf))>=0){if(n>0)out.write(buf,0,n);}return out.toByteArray();}}
    private String enc(String s){try{return java.net.URLEncoder.encode(s,"UTF-8");}catch(Exception e){return s;}}
    private String pathEncode(String s){if(s==null)return "";String[] parts=s.replace('\\','/').split("/");StringBuilder out=new StringBuilder();for(String p:parts){if(p.isEmpty())continue;if(out.length()>0)out.append('/');out.append(enc(p).replace("+","%20"));}return out.toString();}
}
