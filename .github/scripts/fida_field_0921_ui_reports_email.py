from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

# AppDatabase: expose customer/site contact details to reports and delivery UI.
p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/AppDatabase.java')
s = p.read_text()
old = '''    public Row getJob(long id) {
        return one("SELECT j.*, c.name customer_name, s.name site_name, a.name asset_name, a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.id=?", new String[]{String.valueOf(id)});
    }
'''
new = '''    public Row getJob(long id) {
        return one("SELECT j.*, c.name customer_name, c.contact customer_contact, c.phone customer_phone, c.email customer_email, c.address customer_address, s.name site_name, s.contact site_contact, s.phone site_phone, s.address site_address, a.name asset_name, a.tag asset_tag FROM jobs j LEFT JOIN customers c ON c.id=j.customer_id LEFT JOIN sites s ON s.id=j.site_id LEFT JOIN assets a ON a.id=j.asset_id WHERE j.id=?", new String[]{String.valueOf(id)});
    }
'''
s = replace_once(s, old, new, 'getJob contact details')
p.write_text(s)

# Main UI and report delivery flow.
p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = p.read_text()

s = replace_once(
    s,
    '    private ScrollView page(){ScrollView sc=new ScrollView(this);sc.setFillViewport(true);sc.setClipToPadding(false);LinearLayout ll=new LinearLayout(this);ll.setOrientation(LinearLayout.VERTICAL);ll.setPadding(dp(18),dp(18),dp(18),dp(34));sc.addView(ll);sc.setTag(ll);content.addView(sc,new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT));return sc;}',
    '    private ScrollView page(){ScrollView sc=new ScrollView(this);sc.setFillViewport(true);sc.setClipToPadding(false);sc.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS);LinearLayout ll=new LinearLayout(this);ll.setOrientation(LinearLayout.VERTICAL);ll.setPadding(dp(20),dp(20),dp(20),dp(40));sc.addView(ll);sc.setTag(ll);content.addView(sc,new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT));return sc;}',
    'page spacing')

s = replace_once(
    s,
    '    private EditText input(String hint,String value){EditText e=new EditText(this);e.setHint(hint);e.setText(value==null?"":value);e.setTextSize(15);e.setTextColor(textColor());e.setHintTextColor(mutedColor());e.setSingleLine(true);e.setPadding(dp(14),dp(10),dp(14),dp(10));e.setBackground(rounded(surface(),borderColor(),dp(1),dp(13)));e.setSelectAllOnFocus(false);e.setOnFocusChangeListener((v,focused)->e.setBackground(rounded(surface(),focused?ACCENT:borderColor(),focused?dp(2):dp(1),dp(13))));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(58));p.setMargins(0,dp(5),0,dp(5));e.setLayoutParams(p);return e;}',
    '    private EditText input(String hint,String value){EditText e=new EditText(this);e.setHint(hint);e.setText(value==null?"":value);e.setTextSize(15);e.setTextColor(textColor());e.setHintTextColor(mutedColor());e.setSingleLine(true);e.setPadding(dp(16),dp(11),dp(16),dp(11));e.setBackground(rounded(surface(),borderColor(),dp(1),dp(16)));e.setSelectAllOnFocus(false);e.setOnFocusChangeListener((v,focused)->e.setBackground(rounded(surface(),focused?ACCENT:borderColor(),focused?dp(2):dp(1),dp(16))));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(58));p.setMargins(0,dp(6),0,dp(6));e.setLayoutParams(p);return e;}',
    'input styling')

s = replace_once(
    s,
    '    private MaterialButton button(String text){MaterialButton b=new MaterialButton(this);b.setText(text);b.setTextSize(14);b.setAllCaps(false);b.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));b.setCornerRadius(dp(14));b.setInsetTop(0);b.setInsetBottom(0);b.setBackgroundTintList(ColorStateList.valueOf(ACCENT));b.setTextColor(onColor(ACCENT));b.setRippleColor(ColorStateList.valueOf(0x33FFFFFF));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(52));p.setMargins(0,dp(6),0,dp(6));b.setLayoutParams(p);return b;}',
    '    private MaterialButton button(String text){MaterialButton b=new MaterialButton(this);b.setText(text);b.setTextSize(14);b.setAllCaps(false);b.setLetterSpacing(0.01f);b.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));b.setCornerRadius(dp(16));b.setInsetTop(0);b.setInsetBottom(0);b.setBackgroundTintList(ColorStateList.valueOf(ACCENT));b.setTextColor(onColor(ACCENT));b.setRippleColor(ColorStateList.valueOf(0x33FFFFFF));b.setElevation(dp(1));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(54));p.setMargins(0,dp(6),0,dp(6));b.setLayoutParams(p);return b;}',
    'button styling')

s = replace_once(
    s,
    '    private TextView section(String s){TextView t=new TextView(this);t.setText(s);t.setTextSize(16);t.setTextColor(textColor());t.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));t.setPadding(0,dp(23),0,dp(10));GradientDrawable mark=rounded(ACCENT,0,0,dp(2));mark.setBounds(0,0,dp(4),dp(18));t.setCompoundDrawables(mark,null,null,null);t.setCompoundDrawablePadding(dp(9));return t;}',
    '    private TextView section(String s){TextView t=new TextView(this);t.setText(s);t.setTextSize(15);t.setLetterSpacing(0.01f);t.setTextColor(textColor());t.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));t.setPadding(0,dp(26),0,dp(11));GradientDrawable mark=rounded(ACCENT,0,0,dp(3));mark.setBounds(0,0,dp(5),dp(19));t.setCompoundDrawables(mark,null,null,null);t.setCompoundDrawablePadding(dp(10));return t;}',
    'section styling')

old_stat = '    private MaterialCardView stat(String label,long value){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(18));c.setCardElevation(0);c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setGravity(Gravity.CENTER_VERTICAL);l.setPadding(dp(15),dp(13),dp(15),dp(12));View bar=new View(this);bar.setBackground(rounded(ACCENT,0,0,dp(2)));l.addView(bar,new LinearLayout.LayoutParams(dp(30),dp(4)));TextView n=new TextView(this);n.setText(String.valueOf(value));n.setTextSize(27);n.setTextColor(textColor());n.setTypeface(android.graphics.Typeface.create("sans-serif",android.graphics.Typeface.BOLD));n.setPadding(0,dp(5),0,0);TextView lab=new TextView(this);lab.setText(label);lab.setTextSize(12);lab.setTextColor(mutedColor());l.addView(n);l.addView(lab);c.addView(l);return c;}'
new_stat = '    private MaterialCardView stat(String label,long value){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(22));c.setCardElevation(dp(1));c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setGravity(Gravity.CENTER_VERTICAL);l.setPadding(dp(16),dp(14),dp(16),dp(13));LinearLayout top=new LinearLayout(this);top.setGravity(Gravity.CENTER_VERTICAL);View dot=new View(this);dot.setBackground(rounded(ACCENT,0,0,dp(6)));top.addView(dot,new LinearLayout.LayoutParams(dp(9),dp(9)));TextView lab=new TextView(this);lab.setText(label);lab.setTextSize(11);lab.setTextColor(mutedColor());lab.setPadding(dp(7),0,0,0);top.addView(lab);TextView n=new TextView(this);n.setText(String.valueOf(value));n.setTextSize(29);n.setTextColor(textColor());n.setTypeface(android.graphics.Typeface.create("sans-serif",android.graphics.Typeface.BOLD));n.setPadding(0,dp(6),0,0);l.addView(top);l.addView(n);c.addView(l);return c;}'
s = replace_once(s, old_stat, new_stat, 'stat cards')

old_row = '    private MaterialCardView rowCard(String a,String b,String badge){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(18));c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));c.setCardElevation(dp(1));c.setClickable(true);c.setFocusable(true);c.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x12F99D1C));LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,dp(5),0,dp(5));c.setLayoutParams(cp);LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(15),dp(13),dp(13),dp(13));LinearLayout txt=new LinearLayout(this);txt.setOrientation(LinearLayout.VERTICAL);TextView t1=new TextView(this);t1.setText(a);t1.setTextSize(15);t1.setTextColor(textColor());t1.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));TextView t2=new TextView(this);t2.setText(b);t2.setTextSize(12);t2.setTextColor(mutedColor());t2.setPadding(0,dp(4),0,0);txt.addView(t1);txt.addView(t2);row.addView(txt,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));if(badge!=null&&!badge.isEmpty()){TextView x=badgeView(badge);row.addView(x);}c.addView(row);return c;}'
new_row = '    private MaterialCardView rowCard(String a,String b,String badge){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(surface());c.setRadius(dp(20));c.setStrokeColor(borderColor());c.setStrokeWidth(dp(1));c.setCardElevation(dp(1));c.setClickable(true);c.setFocusable(true);c.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x12F99D1C));LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,dp(6),0,dp(6));c.setLayoutParams(cp);LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(16),dp(14),dp(14),dp(14));View rail=new View(this);rail.setBackground(rounded(paleAccentBorder(),0,0,dp(2)));LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(dp(4),dp(38));rp.setMargins(0,0,dp(12),0);row.addView(rail,rp);LinearLayout txt=new LinearLayout(this);txt.setOrientation(LinearLayout.VERTICAL);TextView t1=new TextView(this);t1.setText(a);t1.setTextSize(15);t1.setTextColor(textColor());t1.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));TextView t2=new TextView(this);t2.setText(b);t2.setTextSize(12);t2.setTextColor(mutedColor());t2.setPadding(0,dp(4),0,0);txt.addView(t1);txt.addView(t2);row.addView(txt,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));if(badge!=null&&!badge.isEmpty()){TextView x=badgeView(badge);row.addView(x);}c.addView(row);return c;}'
s = replace_once(s, old_row, new_row, 'row cards')

old_hero = '    private MaterialCardView heroCard(String headline,String copy){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(paleAccent());c.setRadius(dp(22));c.setStrokeColor(paleAccentBorder());c.setStrokeWidth(dp(1));c.setCardElevation(0);LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(18),dp(17),dp(18),dp(17));TextView eyebrow=new TextView(this);eyebrow.setText("FIDA FIELD");eyebrow.setTextSize(10);eyebrow.setLetterSpacing(0.14f);eyebrow.setTextColor(ACCENT);eyebrow.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));TextView h=heading(headline);h.setTextSize(23);h.setPadding(0,dp(6),0,dp(5));TextView p=paragraph(copy);p.setPadding(0,0,0,0);l.addView(eyebrow);l.addView(h);l.addView(p);c.addView(l);LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,0,0,dp(6));c.setLayoutParams(cp);return c;}'
new_hero = '    private MaterialCardView heroCard(String headline,String copy){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(paleAccent());c.setRadius(dp(24));c.setStrokeColor(paleAccentBorder());c.setStrokeWidth(dp(1));c.setCardElevation(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(20),dp(19),dp(20),dp(20));LinearLayout kicker=new LinearLayout(this);kicker.setGravity(Gravity.CENTER_VERTICAL);View dot=new View(this);dot.setBackground(rounded(ACCENT,0,0,dp(6)));kicker.addView(dot,new LinearLayout.LayoutParams(dp(9),dp(9)));TextView eyebrow=new TextView(this);eyebrow.setText("FIDA FIELD  •  OPERATIONS");eyebrow.setTextSize(9);eyebrow.setLetterSpacing(0.12f);eyebrow.setTextColor(brandTextColor());eyebrow.setPadding(dp(8),0,0,0);eyebrow.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));kicker.addView(eyebrow);TextView h=heading(headline);h.setTextSize(24);h.setPadding(0,dp(9),0,dp(5));TextView p=paragraph(copy);p.setPadding(0,0,0,0);l.addView(kicker);l.addView(h);l.addView(p);c.addView(l);LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,0,0,dp(8));c.setLayoutParams(cp);return c;}'
s = replace_once(s, old_hero, new_hero, 'hero card')

old_share = '''    private void generateAndShare(long jobId){
        try{File f=PdfReport.generate(this,db,jobId,prefs);Uri uri=FileProvider.getUriForFile(this,getPackageName()+".files",f);Intent share=new Intent(Intent.ACTION_SEND);share.setType("application/pdf");share.putExtra(Intent.EXTRA_STREAM,uri);share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(share,"Share service report"));}catch(Exception e){error("PDF generation failed",e);}
    }
'''
new_share = '''    private void generateAndShare(long jobId){
        try{
            File f=ProfessionalPdfReport.generate(this,db,jobId,prefs);AppDatabase.Row j=db.getJob(jobId);String email=j.s("customer_email").trim();
            if("Completed".equalsIgnoreCase(j.s("status"))&&!email.isEmpty())showCompletedReportDelivery(f,j);else shareReportFile(f,j,"");
        }catch(Exception e){error("PDF generation failed",e);}
    }

    private void showCompletedReportDelivery(File file,AppDatabase.Row job){
        String email=job.s("customer_email").trim();String customer=job.s("customer_name").isEmpty()?"customer":job.s("customer_name");
        new MaterialAlertDialogBuilder(this).setTitle("Final report ready").setMessage("The completed service report is ready. Email it to "+customer+" at "+email+" or share it with another app.")
                .setNegativeButton("Cancel",null).setNeutralButton("Share…",(d,w)->shareReportFile(file,job,""))
                .setPositiveButton("Email customer",(d,w)->shareReportFile(file,job,email)).show();
    }

    private void shareReportFile(File file,AppDatabase.Row job,String email){
        Uri uri=FileProvider.getUriForFile(this,getPackageName()+".files",file);Intent share=new Intent(Intent.ACTION_SEND);share.setType("application/pdf");share.putExtra(Intent.EXTRA_STREAM,uri);
        if(email!=null&&!email.trim().isEmpty())share.putExtra(Intent.EXTRA_EMAIL,new String[]{email.trim()});
        String company=prefs.getString("company_name","Fidalix Limited");String subject="Service report "+job.s("report_no")+" — "+company;share.putExtra(Intent.EXTRA_SUBJECT,subject);
        String contact=job.s("customer_contact").trim();String greeting=contact.isEmpty()?"Hello,":"Hello "+contact+",";share.putExtra(Intent.EXTRA_TEXT,greeting+"\n\nPlease find attached the completed service report "+job.s("report_no")+" for "+job.s("title")+".\n\nKind regards,\n"+company);
        share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(share,email==null||email.trim().isEmpty()?"Share service report":"Email service report"));
    }
'''
s = replace_once(s, old_share, new_share, 'professional report sharing')

s = replace_once(
    s,
    'b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.20 Test\\nClickable dashboard summaries, Android back navigation, invitation cleanup and cloud sync fixes by Fidalix."));',
    'b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.21 Test\\nModernized interface, professional service reports and optional customer email delivery by Fidalix."));',
    'about version')

p.write_text(s)

# Version bump.
p = Path('fida-field/app/build.gradle')
s = p.read_text()
s = replace_once(s, '        versionCode 23\n        versionName \'0.9.20-test\'\n', '        versionCode 24\n        versionName \'0.9.21-test\'\n', 'version bump')
p.write_text(s)
