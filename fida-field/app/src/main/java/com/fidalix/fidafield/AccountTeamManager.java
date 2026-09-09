package com.fidalix.fidafield;

import android.content.SharedPreferences;

import java.util.UUID;

/** Offline-first workspace/account state. Cloud authentication will replace local identity
 * claims once a backend is connected, while the local workspace remains usable offline. */
public class AccountTeamManager {
    public static final String ROLE_OWNER="Owner";
    public static final String ROLE_ADMIN="Admin";
    public static final String ROLE_TECHNICIAN="Technician";
    public static final String ROLE_VIEWER="Viewer";

    public static final String KEY_WORKSPACE_ID="workspace_id";
    public static final String KEY_WORKSPACE_NAME="workspace_name";
    public static final String KEY_ACCOUNT_NAME="account_name";
    public static final String KEY_ACCOUNT_EMAIL="account_email";
    public static final String KEY_ACCOUNT_ROLE="account_role";

    private final SharedPreferences prefs;
    private final AppDatabase db;

    public AccountTeamManager(SharedPreferences prefs,AppDatabase db){this.prefs=prefs;this.db=db;}

    public boolean hasWorkspace(){return !workspaceId().isEmpty();}
    public String workspaceId(){return prefs.getString(KEY_WORKSPACE_ID,"");}
    public String workspaceName(){return prefs.getString(KEY_WORKSPACE_NAME,"");}
    public String accountName(){return prefs.getString(KEY_ACCOUNT_NAME,"");}
    public String accountEmail(){return prefs.getString(KEY_ACCOUNT_EMAIL,"");}
    public String accountRole(){return prefs.getString(KEY_ACCOUNT_ROLE,hasWorkspace()?ROLE_OWNER:"");}
    public boolean canManageTeam(){String r=accountRole();return ROLE_OWNER.equals(r)||ROLE_ADMIN.equals(r);}

    public void saveOwnerWorkspace(String workspaceName,String accountName,String email){
        String id=workspaceId();if(id.isEmpty())id=UUID.randomUUID().toString();
        prefs.edit().putString(KEY_WORKSPACE_ID,id).putString(KEY_WORKSPACE_NAME,clean(workspaceName))
                .putString(KEY_ACCOUNT_NAME,clean(accountName)).putString(KEY_ACCOUNT_EMAIL,clean(email))
                .putString(KEY_ACCOUNT_ROLE,ROLE_OWNER).apply();
        db.ensureOwnerMember(id,clean(accountName),clean(email));
    }

    public int memberCount(){return hasWorkspace()?db.activeWorkspaceMemberCount(workspaceId()):0;}
    public int pendingInviteCount(){return hasWorkspace()?db.pendingWorkspaceInviteCount(workspaceId()):0;}
    public String teamSummary(){if(!hasWorkspace())return "Workspace not set up";int m=memberCount(),p=pendingInviteCount();return m+" member"+(m==1?"":"s")+(p>0?" • "+p+" pending":"");}
    private String clean(String s){return s==null?"":s.trim();}
}
