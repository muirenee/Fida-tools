package com.fidalix.fidafield;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;

import com.android.billingclient.api.BillingClient;
import com.android.billingclient.api.BillingClientStateListener;
import com.android.billingclient.api.BillingFlowParams;
import com.android.billingclient.api.BillingResult;
import com.android.billingclient.api.PendingPurchasesParams;
import com.android.billingclient.api.ProductDetails;
import com.android.billingclient.api.Purchase;
import com.android.billingclient.api.QueryProductDetailsParams;
import com.android.billingclient.api.QueryPurchasesParams;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Google Play Billing client for the public edition.
 *
 * Purchases are never trusted locally. Every PURCHASED token is sent to the authenticated
 * Supabase Edge Function for Google Play Developer API verification. The app only enables Pro
 * after the server-backed billing_entitlements row says the subscription is active.
 */
public class BillingManager {
    public interface Listener {
        void onBillingChanged();
    }

    public static class ProductOption {
        public final String productId;
        public final String price;
        public ProductOption(String productId,String price){this.productId=productId;this.price=price;}
    }

    private final Context context;
    private final SharedPreferences prefs;
    private final SupabaseClientLite supabase;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final Listener listener;
    private final Map<String,ProductDetails> products=new HashMap<>();
    private BillingClient billingClient;
    private boolean ready=false;

    public BillingManager(Context context,SharedPreferences prefs,Listener listener){
        this.context=context.getApplicationContext();
        this.prefs=prefs;
        this.listener=listener;
        this.supabase=new SupabaseClientLite(prefs);
    }

    public boolean isOpenEdition(){return BuildConfig.OPEN_EDITION;}
    public boolean isReady(){return ready;}
    public String lastResult(){return prefs.getString("billing_last_result",BuildConfig.OPEN_EDITION?"Internal edition · billing not required":"Not checked");}
    public String productId(){return prefs.getString("subscription_product_id","");}
    public String expiry(){return prefs.getString("subscription_expires_at","");}
    public String subscriptionState(){return prefs.getString("subscription_state","");}
    private String workspaceId(){return prefs.getString(AccountTeamManager.KEY_WORKSPACE_ID,"");}
    private boolean hasCloudWorkspace(){return prefs.getBoolean(AccountTeamManager.KEY_CLOUD_WORKSPACE_BOUND,false)&&!workspaceId().isEmpty();}
    private boolean canManageBilling(){String r=prefs.getString(AccountTeamManager.KEY_ACCOUNT_ROLE,"");return AccountTeamManager.ROLE_OWNER.equals(r)||AccountTeamManager.ROLE_ADMIN.equals(r);}

    public void start(){
        if(BuildConfig.OPEN_EDITION)return;
        if(billingClient!=null)return;
        PendingPurchasesParams pending=PendingPurchasesParams.newBuilder().enableOneTimeProducts().build();
        billingClient=BillingClient.newBuilder(context)
                .setListener((billingResult,purchases)->{
                    if(billingResult.getResponseCode()==BillingClient.BillingResponseCode.OK && purchases!=null)processPurchases(purchases);
                    else setResult("Play update · "+billingResult.getDebugMessage());
                })
                .enablePendingPurchases(pending)
                .enableAutoServiceReconnection()
                .build();
        billingClient.startConnection(new BillingClientStateListener(){
            @Override public void onBillingSetupFinished(BillingResult result){
                ready=result.getResponseCode()==BillingClient.BillingResponseCode.OK;
                if(ready){setResult("Google Play connected");queryProducts();refreshPurchases();}
                else setResult("Google Play unavailable · "+result.getDebugMessage());
            }
            @Override public void onBillingServiceDisconnected(){ready=false;notifyChanged();}
        });
        refreshServerEntitlement();
    }

    public void stop(){if(billingClient!=null){billingClient.endConnection();billingClient=null;}ready=false;}

    public List<ProductOption> productOptions(){
        ArrayList<ProductOption> out=new ArrayList<>();
        for(String id:Arrays.asList(EntitlementManager.PRODUCT_PRO_MONTHLY,EntitlementManager.PRODUCT_PRO_ANNUAL)){
            ProductDetails p=products.get(id);if(p!=null)out.add(new ProductOption(id,displayPrice(p)));
        }
        return out;
    }

    public String displayPrice(String productId){ProductDetails p=products.get(productId);return p==null?"Not available":displayPrice(p);}

    private String displayPrice(ProductDetails p){
        try{
            List<ProductDetails.SubscriptionOfferDetails> offers=p.getSubscriptionOfferDetails();
            if(offers!=null&&!offers.isEmpty()&&offers.get(0).getPricingPhases()!=null&&!offers.get(0).getPricingPhases().getPricingPhaseList().isEmpty()){
                List<com.android.billingclient.api.ProductDetails.PricingPhase> phases=offers.get(0).getPricingPhases().getPricingPhaseList();
                return phases.get(phases.size()-1).getFormattedPrice();
            }
        }catch(Exception ignored){}
        return "Available on Google Play";
    }

    public void purchase(Activity activity,String productId){
        if(BuildConfig.OPEN_EDITION){setResult("Billing is disabled in Fidalix Open");return;}
        if(!supabase.hasStoredSession()){setResult("Sign in to your Fida Field account before subscribing");return;}
        if(!hasCloudWorkspace()){setResult("Create or join a cloud workspace before subscribing");return;}
        if(!canManageBilling()){setResult("Only a workspace Owner or Admin can manage the company subscription");return;}
        if(billingClient==null||!ready){setResult("Google Play Billing is not ready yet");start();return;}
        ProductDetails details=products.get(productId);
        if(details==null){setResult("Subscription product is not available to this Play account/track");queryProducts();return;}
        List<ProductDetails.SubscriptionOfferDetails> offers=details.getSubscriptionOfferDetails();
        if(offers==null||offers.isEmpty()){setResult("No eligible Google Play offer is available for this subscription");return;}
        String offerToken=offers.get(0).getOfferToken();
        BillingFlowParams.ProductDetailsParams pd=BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(details).setOfferToken(offerToken).build();
        BillingFlowParams.Builder flow=BillingFlowParams.newBuilder().setProductDetailsParamsList(Arrays.asList(pd));
        String user=supabase.userId();if(user!=null&&!user.isEmpty())flow.setObfuscatedAccountId(hash(user));
        BillingResult result=billingClient.launchBillingFlow(activity,flow.build());
        if(result.getResponseCode()!=BillingClient.BillingResponseCode.OK)setResult("Unable to start purchase · "+result.getDebugMessage());
    }

    public void restore(){
        if(BuildConfig.OPEN_EDITION){setResult("Fidalix Open is already fully enabled");return;}
        if(!supabase.hasStoredSession()){setResult("Sign in to your Fida Field account before restoring purchases");return;}
        refreshPurchases();
    }

    public void refreshPurchases(){
        if(BuildConfig.OPEN_EDITION)return;
        if(billingClient==null||!ready){refreshServerEntitlement();return;}
        QueryPurchasesParams params=QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.SUBS).build();
        billingClient.queryPurchasesAsync(params,(result,purchases)->{
            if(result.getResponseCode()==BillingClient.BillingResponseCode.OK){
                if(purchases==null||purchases.isEmpty())refreshServerEntitlement();
                else processPurchases(purchases);
            }else setResult("Restore failed · "+result.getDebugMessage());
        });
    }

    private void queryProducts(){
        if(billingClient==null||!ready)return;
        List<QueryProductDetailsParams.Product> list=Arrays.asList(
                QueryProductDetailsParams.Product.newBuilder().setProductId(EntitlementManager.PRODUCT_PRO_MONTHLY).setProductType(BillingClient.ProductType.SUBS).build(),
                QueryProductDetailsParams.Product.newBuilder().setProductId(EntitlementManager.PRODUCT_PRO_ANNUAL).setProductType(BillingClient.ProductType.SUBS).build());
        QueryProductDetailsParams params=QueryProductDetailsParams.newBuilder().setProductList(list).build();
        billingClient.queryProductDetailsAsync(params,(result,detailsResult)->{
            if(result.getResponseCode()==BillingClient.BillingResponseCode.OK){
                products.clear();
                for(ProductDetails p:detailsResult.getProductDetailsList())products.put(p.getProductId(),p);
                if(products.isEmpty())setResult("Play Billing connected · subscription products not published for this track yet");
                else notifyChanged();
            }else setResult("Unable to load subscription products · "+result.getDebugMessage());
        });
    }

    private void processPurchases(List<Purchase> purchases){
        boolean found=false;
        for(Purchase p:purchases){
            String product=matchingProduct(p.getProducts());if(product.isEmpty())continue;found=true;
            if(p.getPurchaseState()==Purchase.PurchaseState.PENDING){setResult("Google Play purchase is pending payment/approval");continue;}
            if(p.getPurchaseState()!=Purchase.PurchaseState.PURCHASED)continue;
            verifyOnServer(product,p.getPurchaseToken());
        }
        if(!found)refreshServerEntitlement();
    }

    private String matchingProduct(List<String> ids){
        if(ids==null)return "";
        if(ids.contains(EntitlementManager.PRODUCT_PRO_ANNUAL))return EntitlementManager.PRODUCT_PRO_ANNUAL;
        if(ids.contains(EntitlementManager.PRODUCT_PRO_MONTHLY))return EntitlementManager.PRODUCT_PRO_MONTHLY;
        return "";
    }

    private void verifyOnServer(String productId,String token){
        new Thread(()->{
            try{
                JSONObject body=new JSONObject().put("package_name",BuildConfig.APPLICATION_ID).put("workspace_id",workspaceId()).put("product_id",productId).put("purchase_token",token);
                Object raw=supabase.invokeFunction("verify-play-purchase",body);
                JSONObject o=raw instanceof JSONObject?(JSONObject)raw:new JSONObject();
                boolean active=o.optBoolean("active",false);
                prefs.edit().putBoolean("subscription_pro_enabled",active)
                        .putString("subscription_product_id",o.optString("product_id",productId))
                        .putString("subscription_state",o.optString("subscription_state",""))
                        .putString("subscription_expires_at",o.optString("expires_at",""))
                        .putString("billing_last_result",active?"Verified workspace Pro subscription":"Subscription is not currently active")
                        .apply();
                main.post(this::notifyChanged);
            }catch(Exception e){
                setResultFromBackground("Verification failed · "+safe(e));
                refreshServerEntitlement();
            }
        },"fida-play-verify").start();
    }

    public void refreshServerEntitlement(){
        if(BuildConfig.OPEN_EDITION)return;
        if(!supabase.hasStoredSession()||!hasCloudWorkspace()){
            prefs.edit().putBoolean("subscription_pro_enabled",false).apply();notifyChanged();return;
        }
        new Thread(()->{
            try{
                String workspace=workspaceId();
                JSONArray a=supabase.select("workspace_billing_entitlements","select=active,product_id,subscription_state,expires_at,last_verified_at,purchaser_user_id&workspace_id=eq."+workspace+"&limit=1");
                if(a.length()==0){prefs.edit().putBoolean("subscription_pro_enabled",false).putString("billing_last_result","No verified Pro plan for this workspace").apply();}
                else{
                    JSONObject o=a.getJSONObject(0);boolean active=o.optBoolean("active",false);String expiry=o.optString("expires_at","");
                    if(active&&!expiry.isEmpty()){try{active=java.time.Instant.parse(expiry).isAfter(java.time.Instant.now());}catch(Exception ignored){}}
                    prefs.edit().putBoolean("subscription_pro_enabled",active).putString("subscription_product_id",o.optString("product_id","")).putString("subscription_state",o.optString("subscription_state","")).putString("subscription_expires_at",expiry).putString("billing_last_result",active?"Workspace Pro plan active":"No active Pro plan for this workspace").apply();
                }
                main.post(this::notifyChanged);
            }catch(Exception e){setResultFromBackground("Workspace entitlement refresh failed · "+safe(e));}
        },"fida-entitlement-refresh").start();
    }

    private void setResult(String s){prefs.edit().putString("billing_last_result",s).apply();notifyChanged();}
    private void setResultFromBackground(String s){prefs.edit().putString("billing_last_result",s).apply();main.post(this::notifyChanged);}
    private void notifyChanged(){if(listener!=null)listener.onBillingChanged();}
    private String safe(Exception e){String m=e.getMessage();return m==null||m.trim().isEmpty()?e.getClass().getSimpleName():m;}
    private String hash(String s){
        try{byte[] b=MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8));StringBuilder out=new StringBuilder();for(byte x:b)out.append(String.format("%02x",x));return out.toString();}catch(Exception e){return s.length()>64?s.substring(0,64):s;}
    }
}
