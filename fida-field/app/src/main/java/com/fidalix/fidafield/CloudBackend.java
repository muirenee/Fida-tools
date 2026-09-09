package com.fidalix.fidafield;

/** Contract used by the offline sync engine. A concrete Supabase adapter is plugged into
 * this boundary once the project URL/key and database policies are provisioned. */
public interface CloudBackend {
    String providerName();
    boolean isConfigured();
    boolean isSignedIn();
    String signedInEmail();
    void signOut();
    void sync(Callback callback);

    interface Callback { void onComplete(boolean success,String message); }
}
