package com.fidalix.fidafield;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.net.Uri;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.Locale;

/**
 * Pro-only workspace branding. Settings are retained when Pro is inactive,
 * but custom branding is only applied while a verified/test Pro entitlement is active.
 */
public class BrandingManager {
    public static final int DEFAULT_PRIMARY = 0xFF464B45;
    public static final int DEFAULT_PRIMARY_DARK = 0xFF2F332F;
    public static final int DEFAULT_ACCENT = 0xFFF99D1C;
    public static final int DEFAULT_HIGHLIGHT = 0xFFFFC222;

    public static final String KEY_ENABLED = "custom_branding_enabled";
    public static final String KEY_PRIMARY = "custom_primary_color";
    public static final String KEY_ACCENT = "custom_accent_color";
    public static final String KEY_HIGHLIGHT = "custom_highlight_color";
    public static final String KEY_SETTINGS_DIRTY = "custom_branding_settings_dirty";
    public static final String KEY_LOGO_DIRTY = "custom_branding_logo_dirty";
    public static final String KEY_LOGO_REMOTE_PATH = "custom_branding_logo_remote_path";

    private final SharedPreferences prefs;
    private final boolean pro;

    public BrandingManager(SharedPreferences prefs, boolean pro) {
        this.prefs = prefs;
        this.pro = pro;
    }

    public boolean isActive() {
        return pro && prefs.getBoolean(KEY_ENABLED, false);
    }

    public int primary() {
        return isActive() ? parseColor(prefs.getString(KEY_PRIMARY, "#464B45"), DEFAULT_PRIMARY) : DEFAULT_PRIMARY;
    }

    public int primaryDark() {
        int p = primary();
        return darken(p, 0.28f);
    }

    public int accent() {
        return isActive() ? parseColor(prefs.getString(KEY_ACCENT, "#F99D1C"), DEFAULT_ACCENT) : DEFAULT_ACCENT;
    }

    public int highlight() {
        return isActive() ? parseColor(prefs.getString(KEY_HIGHLIGHT, "#FFC222"), DEFAULT_HIGHLIGHT) : DEFAULT_HIGHLIGHT;
    }

    public String primaryHex() { return normalizeHex(prefs.getString(KEY_PRIMARY, "#464B45"), "#464B45"); }
    public String accentHex() { return normalizeHex(prefs.getString(KEY_ACCENT, "#F99D1C"), "#F99D1C"); }
    public String highlightHex() { return normalizeHex(prefs.getString(KEY_HIGHLIGHT, "#FFC222"), "#FFC222"); }

    public void save(boolean enabled, String primary, String accent, String highlight) {
        SharedPreferences.Editor e = prefs.edit().putBoolean(KEY_ENABLED, enabled);
        e.putString(KEY_PRIMARY, normalizeHex(primary, "#464B45"));
        e.putString(KEY_ACCENT, normalizeHex(accent, "#F99D1C"));
        e.putString(KEY_HIGHLIGHT, normalizeHex(highlight, "#FFC222"));
        e.putBoolean(KEY_SETTINGS_DIRTY,true);
        e.apply();
    }

    public void reset(Context context) {
        prefs.edit().remove(KEY_ENABLED).remove(KEY_PRIMARY).remove(KEY_ACCENT).remove(KEY_HIGHLIGHT)
                .putBoolean(KEY_SETTINGS_DIRTY,true).putBoolean(KEY_LOGO_DIRTY,true).apply();
        File f = logoFile(context); if (f.exists()) f.delete();
    }

    public boolean hasCustomLogo(Context context) { return logoFile(context).isFile(); }

    public Bitmap loadCustomLogo(Context context) {
        if (!isActive()) return null;
        File f = logoFile(context); return f.isFile() ? BitmapFactory.decodeFile(f.getAbsolutePath()) : null;
    }

    public void saveLogo(Context context, Uri uri) throws Exception {
        if (!pro) throw new IllegalStateException("Custom branding requires Pro");
        Bitmap src;
        try (InputStream in = context.getContentResolver().openInputStream(uri)) {
            if (in == null) throw new Exception("Unable to read selected image");
            src = BitmapFactory.decodeStream(in);
        }
        if (src == null) throw new Exception("Unsupported logo image");
        int max = 1400;
        Bitmap out = src;
        if (src.getWidth() > max || src.getHeight() > max) {
            float scale = Math.min((float) max / src.getWidth(), (float) max / src.getHeight());
            out = Bitmap.createScaledBitmap(src, Math.max(1, Math.round(src.getWidth() * scale)), Math.max(1, Math.round(src.getHeight() * scale)), true);
        }
        File dir = logoFile(context).getParentFile(); if (dir != null && !dir.exists() && !dir.mkdirs()) throw new Exception("Unable to create branding folder");
        try (FileOutputStream fos = new FileOutputStream(logoFile(context))) { out.compress(Bitmap.CompressFormat.PNG, 100, fos); }
        if (out != src) out.recycle(); src.recycle();
        prefs.edit().putBoolean(KEY_LOGO_DIRTY,true).apply();
    }

    public void removeLogo(Context context) { File f=logoFile(context); if(f.exists())f.delete(); prefs.edit().putBoolean(KEY_LOGO_DIRTY,true).apply(); }

    public File logoFile(Context context) { return new File(new File(context.getFilesDir(), "branding"), "custom_logo.png"); }

    public static boolean isValidHex(String value) {
        if (value == null) return false;
        String s=value.trim(); if(!s.startsWith("#"))s="#"+s;
        return s.matches("#[0-9A-Fa-f]{6}");
    }

    public static String normalizeHex(String value, String fallback) {
        if (!isValidHex(value)) return fallback;
        String s=value.trim(); if(!s.startsWith("#"))s="#"+s;
        return s.toUpperCase(Locale.US);
    }

    public static int parseColor(String value, int fallback) {
        try { return Color.parseColor(normalizeHex(value, hex(fallback))); } catch (Exception e) { return fallback; }
    }

    public static String hex(int color) { return String.format(Locale.US, "#%06X", 0xFFFFFF & color); }

    public static int darken(int color,float amount){
        amount=Math.max(0f,Math.min(1f,amount));
        int r=Math.round(Color.red(color)*(1f-amount)),g=Math.round(Color.green(color)*(1f-amount)),b=Math.round(Color.blue(color)*(1f-amount));
        return Color.rgb(r,g,b);
    }
}
