package com.fidalix.fidafield;

import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.sqlite.SQLiteDatabase;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.List;
import java.util.Locale;

/**
 * Synchronizes binary field evidence and maintenance history after the core entity pass.
 * Files remain local until Storage acknowledges them. Failed items stay in sync_queue and
 * are retried on the next Sync Now, making intermittent field connectivity safe.
 */
public class CloudMediaSync {
    public static final String BUCKET="fida-field-media";

    public static class Result {
        public int recordsPushed;
        public int recordsPulled;
        public int filesUploaded;
        public int filesDownloaded;
        public int total(){return recordsPushed+recordsPulled+filesUploaded+filesDownloaded;}
    }

    private static class ImageData {
        final byte[] bytes; final String mime; final String ext;
        ImageData(byte[] bytes,String mime,String ext){this.bytes=bytes;this.mime=mime;this.ext=ext;}
    }

    private final Context context;
    private final SharedPreferences prefs;
    private final AppDatabase db;
    private final SupabaseClientLite client;

    public CloudMediaSync(Context context,SharedPreferences prefs,AppDatabase db,SupabaseClientLite client){
        this.context=context.getApplicationContext();this.prefs=prefs;this.db=db;this.client=client;
    }

    public Result sync(String workspaceId,boolean canManageBranding)throws Exception{
        Result r=new Result();
        pushMaintenance(workspaceId,r);pullMaintenance(workspaceId,r);
        pushJobPhotos(workspaceId,r);pullJobPhotos(workspaceId,r);
        pushSignatures(workspaceId,r);pullSignatures(workspaceId,r);
        syncBrandingLogo(workspaceId,canManageBranding,r);
        return r;
    }

    private void pushMaintenance(String workspaceId,Result result)throws Exception{
        List<AppDatabase.Row> pending=db.rows("SELECT * FROM sync_queue WHERE entity_type='maintenance_log' ORDER BY changed_at,id",null);
        for(AppDatabase.Row q:pending){long id=longValue(q.s("entity_id"));if(id<=0)continue;AppDatabase.Row m=db.one("SELECT * FROM maintenance_logs WHERE id=?",new String[]{String.valueOf(id)});if(m.id()==0)continue;
            long assetId=longValue(m.s("asset_id")),jobId=longValue(m.s("job_id"));if(assetId<=0)continue;
            String remote=db.ensureRemoteUuid("maintenance_log",id);JSONObject o=new JSONObject().put("id",remote).put("workspace_id",workspaceId).put("asset_id",db.ensureRemoteUuid("asset",assetId));
            if(jobId>0)o.put("job_id",db.ensureRemoteUuid("job",jobId));else o.put("job_id",JSONObject.NULL);
            o.put("service_date",m.s("service_date")).put("notes",m.s("notes"));putNullable(o,"next_service",m.s("next_service"));
            client.upsert("maintenance_logs","id",o);db.markEntitySynced("maintenance_log",id,remote);result.recordsPushed++;
        }
    }

    private void pullMaintenance(String workspaceId,Result result)throws Exception{
        JSONArray rows=client.select("maintenance_logs","select=*&workspace_id=eq."+workspaceId+"&deleted_at=is.null&order=service_date.asc");SQLiteDatabase d=db.getWritableDatabase();
        for(int i=0;i<rows.length();i++){JSONObject o=rows.getJSONObject(i);String remote=o.optString("id","");if(remote.isEmpty())continue;long assetId=db.localIdForRemote("asset",nullable(o,"asset_id"));if(assetId<=0)continue;long jobId=db.localIdForRemote("job",nullable(o,"job_id"));long local=db.localIdForRemote("maintenance_log",remote);ContentValues v=new ContentValues();v.put("asset_id",assetId);if(jobId>0)v.put("job_id",jobId);else v.putNull("job_id");v.put("service_date",nullable(o,"service_date"));v.put("notes",nullable(o,"notes"));v.put("next_service",nullable(o,"next_service"));
            if(local==0){v.put("created_at",db.now());local=d.insertOrThrow("maintenance_logs",null,v);}else d.update("maintenance_logs",v,"id=?",new String[]{String.valueOf(local)});
            db.bindRemoteUuid("maintenance_log",local,remote);d.delete("sync_queue","entity_type='maintenance_log' AND entity_id=?",new String[]{String.valueOf(local)});result.recordsPulled++;
        }
    }

    private void pushJobPhotos(String workspaceId,Result result)throws Exception{
        List<AppDatabase.Row> pending=db.rows("SELECT * FROM sync_queue WHERE entity_type='job_photo' ORDER BY changed_at,id",null);
        for(AppDatabase.Row q:pending){long photoId=longValue(q.s("entity_id"));if(photoId<=0)continue;AppDatabase.Row p=db.one("SELECT * FROM job_photos WHERE id=?",new String[]{String.valueOf(photoId)});if(p.id()==0)continue;long jobId=longValue(p.s("job_id"));if(jobId<=0)continue;
            ImageData image=readImage(p.s("uri"));String remotePhoto=db.ensureRemoteUuid("job_photo",photoId),remoteJob=db.ensureRemoteUuid("job",jobId);String storage=workspaceId+"/jobs/"+remoteJob+"/photos/"+remotePhoto+"."+image.ext;
            client.uploadObject(BUCKET,storage,image.bytes,image.mime);result.filesUploaded++;
            JSONObject o=new JSONObject().put("id",remotePhoto).put("workspace_id",workspaceId).put("job_id",remoteJob).put("storage_path",storage).put("caption",p.s("caption"));client.upsert("job_photos","id",o);db.markEntitySynced("job_photo",photoId,remotePhoto);result.recordsPushed++;
        }
    }

    private void pullJobPhotos(String workspaceId,Result result)throws Exception{
        JSONArray rows=client.select("job_photos","select=*&workspace_id=eq."+workspaceId+"&deleted_at=is.null&order=created_at.asc");SQLiteDatabase d=db.getWritableDatabase();
        for(int i=0;i<rows.length();i++){JSONObject o=rows.getJSONObject(i);String remote=o.optString("id",""),storage=nullable(o,"storage_path");if(remote.isEmpty()||storage.isEmpty())continue;long jobId=db.localIdForRemote("job",nullable(o,"job_id"));if(jobId<=0)continue;long local=db.localIdForRemote("job_photo",remote);AppDatabase.Row old=local>0?db.one("SELECT * FROM job_photos WHERE id=?",new String[]{String.valueOf(local)}):new AppDatabase.Row();String current=old.s("uri");
            if(local==0||!localRefExists(current)){byte[] bytes=client.downloadObject(BUCKET,storage);File f=cloudFile(workspaceId,"photos",remote,extensionFromPath(storage,"jpg"));write(f,bytes);String uri=Uri.fromFile(f).toString();ContentValues v=new ContentValues();v.put("job_id",jobId);v.put("uri",uri);v.put("caption",nullable(o,"caption"));if(local==0){v.put("created_at",db.now());local=d.insertOrThrow("job_photos",null,v);}else d.update("job_photos",v,"id=?",new String[]{String.valueOf(local)});result.filesDownloaded++;}
            else {ContentValues v=new ContentValues();v.put("job_id",jobId);v.put("caption",nullable(o,"caption"));d.update("job_photos",v,"id=?",new String[]{String.valueOf(local)});}
            db.bindRemoteUuid("job_photo",local,remote);d.delete("sync_queue","entity_type='job_photo' AND entity_id=?",new String[]{String.valueOf(local)});result.recordsPulled++;
        }
    }

    private void pushSignatures(String workspaceId,Result result)throws Exception{
        List<AppDatabase.Row> pending=db.rows("SELECT * FROM sync_queue WHERE entity_type='job_signature' ORDER BY changed_at,id",null);
        for(AppDatabase.Row q:pending){long jobId=longValue(q.s("entity_id"));if(jobId<=0)continue;AppDatabase.Row j=db.one("SELECT * FROM jobs WHERE id=?",new String[]{String.valueOf(jobId)});if(j.id()==0)continue;String remoteJob=db.ensureRemoteUuid("job",jobId),sigUuid=db.ensureRemoteUuid("job_signature",jobId),local=j.s("signature_path");
            if(local.isEmpty()||!new File(local).isFile()){client.update("jobs","id=eq."+remoteJob,new JSONObject().put("signature_path",JSONObject.NULL));db.markEntitySynced("job_signature",jobId,sigUuid);result.recordsPushed++;continue;}
            ImageData image=readImage(local);String storage=workspaceId+"/jobs/"+remoteJob+"/signature/"+sigUuid+"."+image.ext;client.uploadObject(BUCKET,storage,image.bytes,image.mime);result.filesUploaded++;
            client.update("jobs","id=eq."+remoteJob,new JSONObject().put("signature_path",storage).put("customer_name_signed",j.s("customer_name_signed")));db.markEntitySynced("job_signature",jobId,sigUuid);prefs.edit().putString("signature_remote_path_"+jobId,storage).apply();result.recordsPushed++;
        }
    }

    private void pullSignatures(String workspaceId,Result result)throws Exception{
        JSONArray rows=client.select("jobs","select=id,signature_path,customer_name_signed&workspace_id=eq."+workspaceId+"&deleted_at=is.null");SQLiteDatabase d=db.getWritableDatabase();
        for(int i=0;i<rows.length();i++){JSONObject o=rows.getJSONObject(i);String remoteJob=o.optString("id",""),storage=nullable(o,"signature_path");if(remoteJob.isEmpty()||storage.isEmpty())continue;long jobId=db.localIdForRemote("job",remoteJob);if(jobId<=0)continue;String sigUuid=filenameToken(storage),known=db.one("SELECT remote_uuid FROM sync_metadata WHERE entity_type='job_signature' AND entity_id=?",new String[]{String.valueOf(jobId)}).s("remote_uuid");AppDatabase.Row local=db.one("SELECT signature_path FROM jobs WHERE id=?",new String[]{String.valueOf(jobId)});boolean pending=hasPending("job_signature",jobId);
            if(pending)continue;if(!sigUuid.equals(known)||local.s("signature_path").isEmpty()||!new File(local.s("signature_path")).isFile()){byte[] bytes=client.downloadObject(BUCKET,storage);File f=cloudFile(workspaceId,"signatures",remoteJob,extensionFromPath(storage,"png"));write(f,bytes);ContentValues v=new ContentValues();v.put("signature_path",f.getAbsolutePath());v.put("customer_name_signed",nullable(o,"customer_name_signed"));v.put("updated_at",db.now());d.update("jobs",v,"id=?",new String[]{String.valueOf(jobId)});if(!sigUuid.isEmpty())db.bindRemoteUuid("job_signature",jobId,sigUuid);prefs.edit().putString("signature_remote_path_"+jobId,storage).apply();result.filesDownloaded++;}
            result.recordsPulled++;
        }
    }

    private void syncBrandingLogo(String workspaceId,boolean canManage,Result result)throws Exception{
        JSONArray rows=client.select("branding_settings","select=logo_storage_path&workspace_id=eq."+workspaceId);String remotePath=rows.length()>0?nullable(rows.getJSONObject(0),"logo_storage_path"):"";String known=prefs.getString(BrandingManager.KEY_LOGO_REMOTE_PATH,"");boolean dirty=prefs.getBoolean(BrandingManager.KEY_LOGO_DIRTY,false);BrandingManager branding=new BrandingManager(prefs,new EntitlementManager(prefs,db).isPro());File logo=branding.logoFile(context);
        if(canManage&&(dirty||(remotePath.isEmpty()&&logo.isFile()))){String old=remotePath;if(logo.isFile()){byte[] bytes=readFile(logo);String storage=workspaceId+"/branding/logo-"+sha(bytes).substring(0,16)+".png";client.uploadObject(BUCKET,storage,bytes,"image/png");client.update("branding_settings","workspace_id=eq."+workspaceId,new JSONObject().put("logo_storage_path",storage));remotePath=storage;result.filesUploaded++;if(!old.isEmpty()&&!old.equals(storage)){try{client.deleteObject(BUCKET,old);}catch(Exception ignored){}}}
            else {client.update("branding_settings","workspace_id=eq."+workspaceId,new JSONObject().put("logo_storage_path",JSONObject.NULL));remotePath="";if(!old.isEmpty()){try{client.deleteObject(BUCKET,old);}catch(Exception ignored){}}}
            prefs.edit().putBoolean(BrandingManager.KEY_LOGO_DIRTY,false).putString(BrandingManager.KEY_LOGO_REMOTE_PATH,remotePath).apply();known=remotePath;
        }
        if(!remotePath.isEmpty()&&(!logo.isFile()||!remotePath.equals(known))){byte[] bytes=client.downloadObject(BUCKET,remotePath);write(logo,bytes);prefs.edit().putString(BrandingManager.KEY_LOGO_REMOTE_PATH,remotePath).putBoolean(BrandingManager.KEY_LOGO_DIRTY,false).apply();result.filesDownloaded++;}
        else if(remotePath.isEmpty()&&!canManage&&logo.isFile()){logo.delete();prefs.edit().remove(BrandingManager.KEY_LOGO_REMOTE_PATH).apply();}
    }

    private boolean hasPending(String type,long id){return db.count("sync_queue","entity_type=? AND entity_id=?",new String[]{type,String.valueOf(id)})>0;}
    private void putNullable(JSONObject o,String key,String value)throws Exception{if(value==null||value.trim().isEmpty())o.put(key,JSONObject.NULL);else o.put(key,value.trim());}
    private String nullable(JSONObject o,String key){return o==null||o.isNull(key)?"":o.optString(key,"");}
    private long longValue(String s){try{return Long.parseLong(s==null?"0":s);}catch(Exception e){return 0;}}

    private ImageData readImage(String ref)throws Exception{
        byte[] bytes;String mime="";String source=ref==null?"":ref;
        if(source.startsWith("content://")||source.startsWith("android.resource://")){Uri u=Uri.parse(source);mime=context.getContentResolver().getType(u);try(InputStream in=context.getContentResolver().openInputStream(u)){if(in==null)throw new Exception("Unable to read local image");bytes=readAll(in);}}
        else {File f;if(source.startsWith("file://"))f=new File(Uri.parse(source).getPath());else f=new File(source);if(!f.isFile())throw new Exception("Local media file is missing");mime=mimeFromName(f.getName());bytes=readFile(f);}
        if(mime==null)mime="";String ext=extensionForMime(mime,source);if(!mime.equals("image/jpeg")&&!mime.equals("image/png")&&!mime.equals("image/webp")){Bitmap b=BitmapFactory.decodeByteArray(bytes,0,bytes.length);if(b==null)throw new Exception("Unsupported image format");ByteArrayOutputStream out=new ByteArrayOutputStream();b.compress(Bitmap.CompressFormat.PNG,100,out);b.recycle();bytes=out.toByteArray();mime="image/png";ext="png";}
        if(bytes.length>10*1024*1024)throw new Exception("Media file is larger than the 10 MB cloud limit");return new ImageData(bytes,mime,ext);
    }

    private boolean localRefExists(String ref){try{if(ref==null||ref.isEmpty())return false;if(ref.startsWith("content://")||ref.startsWith("android.resource://")){try(InputStream in=context.getContentResolver().openInputStream(Uri.parse(ref))){return in!=null;}}if(ref.startsWith("file://"))return new File(Uri.parse(ref).getPath()).isFile();return new File(ref).isFile();}catch(Exception e){return false;}}
    private File cloudFile(String workspace,String kind,String id,String ext){File dir=new File(new File(new File(context.getFilesDir(),"cloud_media"),workspace),kind);if(!dir.exists())dir.mkdirs();return new File(dir,id+"."+ext);}
    private void write(File f,byte[] data)throws Exception{File dir=f.getParentFile();if(dir!=null&&!dir.exists()&&!dir.mkdirs())throw new Exception("Unable to create cloud media folder");try(FileOutputStream out=new FileOutputStream(f)){out.write(data);}}
    private byte[] readFile(File f)throws Exception{try(InputStream in=new FileInputStream(f)){return readAll(in);}}
    private byte[] readAll(InputStream in)throws Exception{ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buf=new byte[16384];int n;while((n=in.read(buf))>=0){if(n>0)out.write(buf,0,n);}return out.toByteArray();}
    private String mimeFromName(String name){String n=name==null?"":name.toLowerCase(Locale.US);if(n.endsWith(".png"))return "image/png";if(n.endsWith(".webp"))return "image/webp";return "image/jpeg";}
    private String extensionForMime(String mime,String source){if("image/png".equalsIgnoreCase(mime))return "png";if("image/webp".equalsIgnoreCase(mime))return "webp";String s=source==null?"":source.toLowerCase(Locale.US);if(s.endsWith(".png"))return "png";if(s.endsWith(".webp"))return "webp";return "jpg";}
    private String extensionFromPath(String path,String fallback){if(path==null)return fallback;int dot=path.lastIndexOf('.');if(dot<0||dot==path.length()-1)return fallback;String e=path.substring(dot+1).toLowerCase(Locale.US);return e.matches("[a-z0-9]{1,5}")?e:fallback;}
    private String filenameToken(String path){if(path==null)return "";String p=path;int slash=p.lastIndexOf('/');if(slash>=0)p=p.substring(slash+1);int dot=p.lastIndexOf('.');if(dot>0)p=p.substring(0,dot);return p;}
    private String sha(byte[] data)throws Exception{MessageDigest md=MessageDigest.getInstance("SHA-256");byte[] h=md.digest(data);StringBuilder b=new StringBuilder();for(byte x:h)b.append(String.format(Locale.US,"%02x",x&0xff));return b.toString();}
}
