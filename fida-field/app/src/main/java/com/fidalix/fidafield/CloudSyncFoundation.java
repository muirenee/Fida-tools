package com.fidalix.fidafield;

import android.content.SharedPreferences;

import java.util.UUID;

/**
 * Local-only cloud-sync foundation. No network traffic is performed in 0.9.5.
 * The stable device ID and database change queue are intended for the future
 * authenticated sync service.
 */
public class CloudSyncFoundation {
    private final SharedPreferences prefs;
    private final AppDatabase db;

    public CloudSyncFoundation(SharedPreferences prefs, AppDatabase db) {
        this.prefs = prefs;
        this.db = db;
    }

    public String deviceId() {
        String id = prefs.getString("cloud_device_id", "");
        if (id == null || id.isEmpty()) {
            id = UUID.randomUUID().toString();
            prefs.edit().putString("cloud_device_id", id).apply();
        }
        return id;
    }

    public long pendingChanges() {
        return db.count("sync_queue", null, null);
    }
}
