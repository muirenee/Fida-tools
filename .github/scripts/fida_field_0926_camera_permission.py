from pathlib import Path

main_path = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
gradle_path = Path('fida-field/app/build.gradle')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'0.9.26 patch failed: {label} pattern not found')
    return text.replace(old, new, 1)

s = main_path.read_text()

s = replace_once(
    s,
    '    private ActivityResultLauncher<Intent> cameraLauncher;\n',
    '    private ActivityResultLauncher<Intent> cameraLauncher;\n'
    '    private ActivityResultLauncher<String> cameraPermissionLauncher;\n',
    'camera permission launcher field'
)

s = replace_once(
    s,
    '    private void registerLaunchers(){\n'
    '        cameraLauncher=registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result->{\n',
    '    private void registerLaunchers(){\n'
    '        cameraPermissionLauncher=registerForActivityResult(new ActivityResultContracts.RequestPermission(), granted->{\n'
    '            if(granted&&photoJobId>0){long jobId=photoJobId;launchCameraCapture(jobId);}\n'
    '            else{photoJobId=0;if(!granted)showCameraPermissionRequired();}\n'
    '        });\n'
    '        cameraLauncher=registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result->{\n',
    'camera permission launcher registration'
)

old_capture = '''    private void capturePhoto(long jobId){\n        try{ContentValues values=new ContentValues();values.put(MediaStore.Images.Media.DISPLAY_NAME,"FidaField-"+System.currentTimeMillis()+".jpg");values.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");values.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/FidaField");Uri uri=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);if(uri==null)throw new Exception("Could not create photo destination");Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);intent.putExtra(MediaStore.EXTRA_OUTPUT,uri);intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);photoJobId=jobId;pendingPhotoUri=uri;cameraLauncher.launch(intent);}catch(Exception e){error("Camera unavailable",e);}\n    }\n'''

new_capture = '''    private void capturePhoto(long jobId){\n        if(ContextCompat.checkSelfPermission(this,Manifest.permission.CAMERA)!=android.content.pm.PackageManager.PERMISSION_GRANTED){\n            photoJobId=jobId;cameraPermissionLauncher.launch(Manifest.permission.CAMERA);return;\n        }\n        launchCameraCapture(jobId);\n    }\n\n    private void launchCameraCapture(long jobId){\n        Uri uri=null;\n        try{\n            ContentValues values=new ContentValues();values.put(MediaStore.Images.Media.DISPLAY_NAME,"FidaField-"+System.currentTimeMillis()+".jpg");values.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");\n            if(Build.VERSION.SDK_INT>=29)values.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/FidaField");\n            uri=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);if(uri==null)throw new Exception("Could not create photo destination");\n            Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);intent.putExtra(MediaStore.EXTRA_OUTPUT,uri);intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);photoJobId=jobId;pendingPhotoUri=uri;cameraLauncher.launch(intent);\n        }catch(Exception e){\n            if(uri!=null)try{getContentResolver().delete(uri,null,null);}catch(Exception ignored){}pendingPhotoUri=null;photoJobId=0;error("Camera unavailable",e);\n        }\n    }\n\n    private void showCameraPermissionRequired(){\n        new MaterialAlertDialogBuilder(this).setTitle("Camera permission required").setMessage("Fida Field needs camera access to take job photos. Allow Camera permission, then try Add photo again.")\n                .setNegativeButton("Cancel",null).setPositiveButton("Open app settings",(d,w)->{Intent i=new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName()));startActivity(i);}).show();\n    }\n'''

s = replace_once(s, old_capture, new_capture, 'camera capture permission flow')
main_path.write_text(s)

g = gradle_path.read_text()
g = replace_once(g, '        versionCode 28\n', '        versionCode 29\n', 'version code')
g = replace_once(g, "        versionName '0.9.25-test'\n", "        versionName '0.9.26-test'\n", 'version name')
gradle_path.write_text(g)

print('Fida Field 0.9.26 camera permission fix applied')
