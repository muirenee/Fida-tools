package com.fidalix.fidafield;

import android.content.SharedPreferences;

import java.util.Calendar;
import java.util.Locale;

/**
 * Central commercial-entitlement rules. 0.9.5 uses a test Pro switch only;
 * future Google Play Billing can replace the entitlement source without
 * changing feature checks throughout the app.
 */
public class EntitlementManager {
    public static final int FREE_MONTHLY_REPORT_LIMIT = 5;
    public static final String PRODUCT_PRO_MONTHLY = "fida_field_pro_monthly";
    public static final String PRODUCT_PRO_ANNUAL = "fida_field_pro_annual";

    private final SharedPreferences prefs;
    private final AppDatabase db;

    public EntitlementManager(SharedPreferences prefs, AppDatabase db) {
        this.prefs = prefs;
        this.db = db;
    }

    public boolean isPro() {
        // Production billing/account entitlement can set subscription_pro_enabled.
        // The test switch remains available only during development builds.
        return prefs.getBoolean("subscription_pro_enabled", false) || prefs.getBoolean("test_pro_enabled", false);
    }

    public String planName() {
        return isPro() ? "Pro (test entitlement)" : "Free";
    }

    public int reportsCreatedThisMonth() {
        Calendar c = Calendar.getInstance();
        String monthPrefix = String.format(Locale.US, "%04d-%02d", c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1);
        return (int) db.count("jobs", "created_at LIKE ?", new String[]{monthPrefix + "%"});
    }

    public int freeReportsRemaining() {
        return Math.max(0, FREE_MONTHLY_REPORT_LIMIT - reportsCreatedThisMonth());
    }

    public boolean canCreateReport() {
        return isPro() || reportsCreatedThisMonth() < FREE_MONTHLY_REPORT_LIMIT;
    }

    public boolean canExportCsv() {
        return isPro();
    }

    public boolean canUseCustomBranding() {
        return isPro();
    }

    public String usageSummary() {
        if (isPro()) return "Unlimited service reports";
        return reportsCreatedThisMonth() + "/" + FREE_MONTHLY_REPORT_LIMIT + " reports this month";
    }
}
