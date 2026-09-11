from pathlib import Path

p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = p.read_text()
start = s.index('    private void shareReportFile(File file,AppDatabase.Row job,String email){')
end = s.index('\n    private ', start + 8)
method = r'''    private void shareReportFile(File file,AppDatabase.Row job,String email){
        Uri uri=FileProvider.getUriForFile(this,getPackageName()+".files",file);
        Intent share=new Intent(Intent.ACTION_SEND);
        share.setType("application/pdf");
        share.putExtra(Intent.EXTRA_STREAM,uri);
        if(email!=null&&!email.trim().isEmpty())share.putExtra(Intent.EXTRA_EMAIL,new String[]{email.trim()});
        String company=prefs.getString("company_name","Fidalix Limited");
        String subject="Service report "+job.s("report_no")+" — "+company;
        share.putExtra(Intent.EXTRA_SUBJECT,subject);
        String contact=job.s("customer_contact").trim();
        String greeting=contact.isEmpty()?"Hello,":"Hello "+contact+",";
        share.putExtra(Intent.EXTRA_TEXT,greeting+"\n\nPlease find attached the completed service report "+job.s("report_no")+" for "+job.s("title")+".\n\nKind regards,\n"+company);
        share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivity(Intent.createChooser(share,email==null||email.trim().isEmpty()?"Share service report":"Email service report"));
    }
'''
s = s[:start] + method + s[end:]
p.write_text(s)
