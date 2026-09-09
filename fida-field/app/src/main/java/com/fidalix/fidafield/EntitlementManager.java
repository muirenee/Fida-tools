package com.fidalix.fidafield;

import android.content.SharedPreferences;

import java.util.Calendar;
import java.util.Locale;

/** Central commercial entitlement rules shared by the Play and Fidalix Open editions. */
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

    public boolean isOpenEdition() {
        return BuildConfig.OPEN_EDITION;
    }

    public boolean isPro() {
        // The internal Fidalix Open build intentionally bypasses Google Play Billing.
        // Public Play builds only trust the server-backed verified entitlement flag.
        return isOpenEdition() || prefs.getBoolean("subscription_pro_enabled", false);
    }

    public String planName() {
        if (isOpenEdition()) return "Fidalix Open";
        return isPro() ? "Pro" : "Free";
    }

    public String entitlementSource() {
        if (isOpenEdition()) return "Internal Fidalix edition";
        if (isPro()) return "Verified company/workspace Google Play subscription";
        return "No active Pro subscription";
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

    public boolean canExportCsv() { return isPro(); }
    public boolean canUseCustomBranding() { return isPro(); }

    public String usageSummary() {
        if (isOpenEdition()) return "Unlimited · internal edition";
        if (isPro()) return "Unlimited service reports";
        return reportsCreatedThisMonth() + "/" + FREE_MONTHLY_REPORT_LIMIT + " reports this month";
    }
}
