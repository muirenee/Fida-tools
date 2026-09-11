from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if old not in text:
        raise AssertionError(f"missing anchor: {label}")
    return text.replace(old, new, 1)

p = Path('fida-field/app/src/main/java/com/fidalix/fidafield/MainActivity.java')
s = p.read_text()

# Use one clear field-service term throughout the UI. "Customers" maps directly to
# the existing customer -> site -> asset -> job data model and avoids implying that
# every service recipient is a commercial partner.
s = replace_once(
    s,
    'bottom.getMenu().add(0,MENU_CUSTOMERS,2,"Clients").setIcon(R.drawable.ic_customers);',
    'bottom.getMenu().add(0,MENU_CUSTOMERS,2,"Customers").setIcon(R.drawable.ic_customers);',
    'bottom navigation customer label')

s = replace_once(
    s,
    'setHeader("Customers","Clients, sites & service history")',
    'setHeader("Customers","Customers, sites & service history")',
    'customer page subtitle')

# Tighten the home hero so more operational content is visible above the fold.
s = replace_once(
    s,
    'String tech=prefs.getString("technician_name","");b.addView(heroCard(tech.isEmpty()?"Field service, organized.":"Hello, "+tech,"Capture work, service history and customer-ready reports — even offline."));',
    'String tech=prefs.getString("technician_name","");b.addView(heroCard(tech.isEmpty()?"Field service, organized.":"Hello, "+tech,"Jobs, service history and customer-ready reports — even offline."));',
    'dashboard hero copy')

old_hero = '    private MaterialCardView heroCard(String headline,String copy){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(paleAccent());c.setRadius(dp(24));c.setStrokeColor(paleAccentBorder());c.setStrokeWidth(dp(1));c.setCardElevation(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(20),dp(19),dp(20),dp(20));LinearLayout kicker=new LinearLayout(this);kicker.setGravity(Gravity.CENTER_VERTICAL);View dot=new View(this);dot.setBackground(rounded(ACCENT,0,0,dp(6)));kicker.addView(dot,new LinearLayout.LayoutParams(dp(9),dp(9)));TextView eyebrow=new TextView(this);eyebrow.setText("FIDA FIELD  •  OPERATIONS");eyebrow.setTextSize(9);eyebrow.setLetterSpacing(0.12f);eyebrow.setTextColor(brandTextColor());eyebrow.setPadding(dp(8),0,0,0);eyebrow.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));kicker.addView(eyebrow);TextView h=heading(headline);h.setTextSize(24);h.setPadding(0,dp(9),0,dp(5));TextView p=paragraph(copy);p.setPadding(0,0,0,0);l.addView(kicker);l.addView(h);l.addView(p);c.addView(l);LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,0,0,dp(8));c.setLayoutParams(cp);return c;}'
new_hero = '    private MaterialCardView heroCard(String headline,String copy){MaterialCardView c=new MaterialCardView(this);c.setCardBackgroundColor(paleAccent());c.setRadius(dp(22));c.setStrokeColor(paleAccentBorder());c.setStrokeWidth(dp(1));c.setCardElevation(dp(1));LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(18),dp(15),dp(18),dp(16));LinearLayout kicker=new LinearLayout(this);kicker.setGravity(Gravity.CENTER_VERTICAL);View dot=new View(this);dot.setBackground(rounded(ACCENT,0,0,dp(6)));kicker.addView(dot,new LinearLayout.LayoutParams(dp(8),dp(8)));TextView eyebrow=new TextView(this);eyebrow.setText("FIDA FIELD  •  OPERATIONS");eyebrow.setTextSize(9);eyebrow.setLetterSpacing(0.12f);eyebrow.setTextColor(brandTextColor());eyebrow.setPadding(dp(8),0,0,0);eyebrow.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.BOLD));kicker.addView(eyebrow);TextView h=heading(headline);h.setTextSize(22);h.setPadding(0,dp(7),0,dp(3));TextView p=paragraph(copy);p.setTextSize(13);p.setPadding(0,0,0,0);l.addView(kicker);l.addView(h);l.addView(p);c.addView(l);LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);cp.setMargins(0,0,0,dp(8));c.setLayoutParams(cp);return c;}'
s = replace_once(s, old_hero, new_hero, 'compact hero card')

# Reduce dashboard metric height slightly while preserving touch targets and readability.
s = s.replace('new LinearLayout.LayoutParams(0,dp(108),1)', 'new LinearLayout.LayoutParams(0,dp(102),1)')

# Zero-value metric cards remain non-clickable and now also look intentionally inactive.
old_dash_stat = '''    private MaterialCardView dashboardStat(String label,long value,View.OnClickListener action){
        MaterialCardView c=stat(label,value);
        if(value>0&&action!=null){c.setClickable(true);c.setFocusable(true);c.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x12F99D1C));c.setOnClickListener(action);}
        else{c.setClickable(false);c.setFocusable(false);}
        return c;
    }
'''
new_dash_stat = '''    private MaterialCardView dashboardStat(String label,long value,View.OnClickListener action){
        MaterialCardView c=stat(label,value);
        if(value>0&&action!=null){
            c.setClickable(true);c.setFocusable(true);c.setAlpha(1f);c.setRippleColor(ColorStateList.valueOf(isNight()?0x22F99D1C:0x12F99D1C));c.setOnClickListener(action);
        }else{
            c.setClickable(false);c.setFocusable(false);c.setCardElevation(0);c.setCardBackgroundColor(softSurface());c.setStrokeColor(isNight()?0xFF343934:0xFFE7E9E6);c.setAlpha(isNight()?0.74f:0.72f);
        }
        return c;
    }
'''
s = replace_once(s, old_dash_stat, new_dash_stat, 'inactive zero dashboard metrics')

s = replace_once(
    s,
    'b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.21 Test\\nModernized interface, professional service reports and optional customer email delivery by Fidalix."));',
    'b.addView(section("About"));b.addView(paragraph("Fida Field 0.9.22 Test\\nRefined home dashboard, consistent customer terminology, professional reports and customer email delivery by Fidalix."));',
    'about version')

p.write_text(s)

# Version bump.
p = Path('fida-field/app/build.gradle')
s = p.read_text()
s = replace_once(s, "        versionCode 24\n        versionName '0.9.21-test'\n", "        versionCode 25\n        versionName '0.9.22-test'\n", 'version bump')
p.write_text(s)

# Trigger marker for the 0.9.22 build workflow.
