package com.fidalix.fidafield;

import android.content.SharedPreferences;

import java.util.UUID;

/** Offline-first workspace/account state. A local workspace can exist without cloud access;
 * once Supabase membership is resolved the same local data is bound to the cloud workspace. */
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
    public static final String KEY_CLOUD_WORKSPACE_BOUND="cloud_workspace_bound";
    public static final String KEY_CLOUD_USER_ID="cloud_user_id";

    private final SharedPreferences prefs;
    private final AppDatabase db;

    public AccountTeamManager(SharedPreferences prefs,AppDatabase db){this.prefs=prefs;this.db=db;}

    public boolean hasWorkspace(){return !workspaceId().isEmpty();}
    public boolean hasCloudWorkspace(){return hasWorkspace()&&prefs.getBoolean(KEY_CLOUD_WORKSPACE_BOUND,false);}
    public String workspaceId(){return prefs.getString(KEY_WORKSPACE_ID,"");}
    public String workspaceName(){return prefs.getString(KEY_WORKSPACE_NAME,"");}
    public String accountName(){return prefs.getString(KEY_ACCOUNT_NAME,"");}
    public String accountEmail(){return prefs.getString(KEY_ACCOUNT_EMAIL,"");}
    public String accountRole(){return prefs.getString(KEY_ACCOUNT_ROLE,hasWorkspace()?ROLE_OWNER:"");}
    public String cloudUserId(){return prefs.getString(KEY_CLOUD_USER_ID,"");}
    public boolean canManageTeam(){String r=accountRole();return ROLE_OWNER.equals(r)||ROLE_ADMIN.equals(r);}

    public void saveOwnerWorkspace(String workspaceName,String accountName,String email){
        String id=workspaceId();if(id.isEmpty())id=UUID.randomUUID().toString();
        prefs.edit().putString(KEY_WORKSPACE_ID,id).putString(KEY_WORKSPACE_NAME,clean(workspaceName))
                .putString(KEY_ACCOUNT_NAME,clean(accountName)).putString(KEY_ACCOUNT_EMAIL,clean(email))
                .putString(KEY_ACCOUNT_ROLE,ROLE_OWNER).apply();
        db.ensureOwnerMember(id,clean(accountName),clean(email));
    }

    public void bindCloudAccount(String userId,String name,String email){
        SharedPreferences.Editor e=prefs.edit().putString(KEY_CLOUD_USER_ID,clean(userId)).putString(KEY_ACCOUNT_EMAIL,clean(email));
        if(name!=null&&!name.trim().isEmpty())e.putString(KEY_ACCOUNT_NAME,clean(name));e.apply();
    }

    public void bindCloudWorkspace(String cloudWorkspaceId,String name,String role){
        String old=workspaceId();String normalizedRole=normalizeRole(role);
        prefs.edit().putString(KEY_WORKSPACE_ID,clean(cloudWorkspaceId)).putString(KEY_WORKSPACE_NAME,clean(name))
                .putString(KEY_ACCOUNT_ROLE,normalizedRole).putBoolean(KEY_CLOUD_WORKSPACE_BOUND,true)
                .putString(CloudSyncFoundation.KEY_WORKSPACE_ACCESS_ID,clean(cloudWorkspaceId)).putString(CloudSyncFoundation.KEY_WORKSPACE_ACCESS_STATE,CloudSyncFoundation.ACCESS_ACTIVE).apply();
        if(!old.isEmpty()&&!old.equals(cloudWorkspaceId))db.rebindWorkspace(old,cloudWorkspaceId);
    }

    public void clearCloudBinding(){prefs.edit().putBoolean(KEY_CLOUD_WORKSPACE_BOUND,false).remove(KEY_CLOUD_USER_ID).apply();}

    public int memberCount(){return hasWorkspace()?db.activeWorkspaceMemberCount(workspaceId()):0;}
    public int pendingInviteCount(){return hasWorkspace()?db.pendingWorkspaceInviteCount(workspaceId()):0;}
    public String teamSummary(){if(!hasWorkspace())return "Workspace not set up";int m=memberCount(),p=pendingInviteCount();return m+" member"+(m==1?"":"s")+(p>0?" • "+p+" pending":"");}
    public static String normalizeRole(String role){if(role==null)return "";String r=role.trim().toLowerCase();if("owner".equals(r))return ROLE_OWNER;if("admin".equals(r))return ROLE_ADMIN;if("viewer".equals(r))return ROLE_VIEWER;if("technician".equals(r))return ROLE_TECHNICIAN;return role.trim();}
    public static String normalizeStatus(String status){if(status==null||status.isEmpty())return "";String s=status.trim().toLowerCase();return Character.toUpperCase(s.charAt(0))+s.substring(1);}
    private String clean(String s){return s==null?"":s.trim();}
}
