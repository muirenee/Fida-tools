import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json"}});
const text=(v:unknown,max=5000)=>String(v??"").trim().slice(0,max);
const validUntil=(v:unknown)=>!v||Number.isNaN(Date.parse(String(v)))||Date.parse(String(v))>Date.now();
const monthBounds=()=>{const d=new Date();const start=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),1));const end=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,1));return {start:start.toISOString(),end:end.toISOString()};};

const extractOutputText=(payload:any)=>{
  if(typeof payload?.output_text==="string"&&payload.output_text.trim())return payload.output_text.trim();
  let out="";
  for(const item of Array.isArray(payload?.output)?payload.output:[]){
    if(item?.type!=="message"||!Array.isArray(item?.content))continue;
    for(const part of item.content){if(part?.type==="output_text"&&typeof part?.text==="string")out+=part.text;}
  }
  return out.trim();
};
const parseJsonText=(raw:string)=>{let v=raw.trim();if(v.startsWith("```"))v=v.replace(/^```(?:json)?\s*/i,"").replace(/\s*```$/i,"").trim();return JSON.parse(v);};

Deno.serve(async(req:Request)=>{
  if(req.method!=="POST")return json({ok:false,message:"Method not allowed"},405);
  let usageEventId="";
  try{
    const auth=req.headers.get("Authorization")??"";const jwt=auth.startsWith("Bearer ")?auth.slice(7):"";
    if(!jwt)return json({ok:false,message:"Authentication required"},401);
    const admin=createClient(Deno.env.get("SUPABASE_URL")!,Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:userData,error:userError}=await admin.auth.getUser(jwt);const user=userData?.user;
    if(userError||!user)return json({ok:false,message:"Invalid session"},401);
    const body=await req.json().catch(()=>({}));const workspaceId=text(body?.workspace_id,80);const action=text(body?.action,30)||"assist";
    if(!workspaceId)return json({ok:false,message:"Workspace is required"},400);

    const {data:member}=await admin.from("workspace_members").select("role,status").eq("workspace_id",workspaceId).eq("user_id",user.id).maybeSingle();
    const role=String(member?.role??"").toLowerCase();
    if(String(member?.status??"").toLowerCase()!=="active")return json({ok:false,message:"Active workspace access required"},403);

    const {data:config}=await admin.from("ai_service_config").select("enabled,default_monthly_limit,per_user_minute_limit").eq("singleton",true).maybeSingle();
    const serviceEnabled=Boolean(config?.enabled);const defaultLimit=Math.max(1,Number(config?.default_monthly_limit??100));const perMinute=Math.max(1,Number(config?.per_user_minute_limit??5));
    const {data:override}=await admin.from("ai_workspace_overrides").select("enabled,monthly_limit,expires_at").eq("workspace_id",workspaceId).maybeSingle();
    const {data:billing}=await admin.from("workspace_billing_entitlements").select("active,expires_at").eq("workspace_id",workspaceId).maybeSingle();
    const overrideActive=Boolean(override?.enabled)&&validUntil(override?.expires_at);const billingActive=Boolean(billing?.active)&&validUntil(billing?.expires_at);const entitled=overrideActive||billingActive;
    const monthlyLimit=Math.max(1,Number(override?.monthly_limit??defaultLimit));

    const bounds=monthBounds();
    const {data:monthRows,count:usedCount}=await admin.from("ai_usage_events").select("input_tokens,output_tokens",{count:"exact"}).eq("workspace_id",workspaceId).gte("created_at",bounds.start).lt("created_at",bounds.end);
    const inputTokens=(monthRows??[]).reduce((n:number,r:any)=>n+Number(r?.input_tokens??0),0);const outputTokens=(monthRows??[]).reduce((n:number,r:any)=>n+Number(r?.output_tokens??0),0);const used=Number(usedCount??0);
    const usage={enabled:serviceEnabled,entitled,monthly_limit:monthlyLimit,used_this_month:used,remaining:Math.max(monthlyLimit-used,0),input_tokens:inputTokens,output_tokens:outputTokens,period_start:bounds.start.slice(0,10),period_end:new Date(Date.parse(bounds.end)-86400000).toISOString().slice(0,10)};

    if(action==="usage"){
      if(role!=="owner"&&role!=="admin")return json({ok:false,message:"Owner or Admin access required"},403);
      return json({ok:true,usage});
    }

    if(!serviceEnabled)return json({ok:false,message:"AI report assistant is temporarily disabled by Fidalix",usage},503);
    if(!entitled)return json({ok:false,message:"AI report assistant requires an active Pro workspace entitlement",usage},403);

    const apiKey=Deno.env.get("OPENAI_API_KEY")??"";
    if(!apiKey)return json({ok:false,configured:false,message:"AI report assistant is not configured yet.",usage},503);

    const {data:claimData,error:claimError}=await admin.rpc("claim_ai_usage",{p_workspace_id:workspaceId,p_user_id:user.id,p_monthly_limit:monthlyLimit,p_per_user_minute_limit:perMinute});
    if(claimError)throw claimError;const claim=Array.isArray(claimData)?claimData[0]:claimData;
    if(!claim?.allowed)return json({ok:false,message:String(claim?.reason||"AI request limit reached"),usage:{...usage,used_this_month:Number(claim?.used_this_month??used),remaining:Math.max(monthlyLimit-Number(claim?.used_this_month??used),0)}},429);
    usageEventId=String(claim.event_id??"");const claimedUsed=Number(claim.used_this_month??used+1);

    const context={title:text(body?.title,500),reported_problem:text(body?.problem,5000),diagnosis_notes:text(body?.diagnosis,5000),work_notes:text(body?.work_done,5000),parts_materials:text(body?.parts,3000)};
    if(!context.reported_problem&&!context.diagnosis_notes&&!context.work_notes&&!context.parts_materials){if(usageEventId)await admin.rpc("complete_ai_usage",{p_event_id:usageEventId,p_status:"failed",p_input_tokens:0,p_output_tokens:0});return json({ok:false,message:"Enter some service notes before using AI assist."},400);}

    const model=Deno.env.get("OPENAI_MODEL")||"gpt-5.6-luna";
    const instructions=`You are Fida Field's professional field-service report writing assistant. Your job is to EXPAND terse technician notes into polished, customer-ready service report prose while preserving the facts exactly.

Core behavior:
- Do not merely echo short input. Unless a field is already well-written and complete, rewrite it into fuller professional sentences and make it materially clearer and more detailed.
- For a non-empty diagnosis field, normally produce about 2-4 concise sentences. Explain the stated fault/condition, what it means operationally, and the relationship between the stated observations, but only where that meaning follows directly from the technician's words.
- For a non-empty work_done field, normally produce about 2-5 concise sentences. Turn fragments into a logical sequence of actions performed and stated results. Use professional verbs such as inspected, checked, configured, replaced, cleaned, reconnected, tested, restored, or verified ONLY when those actions are actually present in the input.
- For a non-empty parts field, turn shorthand into a clear professional materials/parts statement. Keep quantities, model names, serials and part names exactly when supplied.
- Use the reported problem and job title only as context for wording; never convert the reported problem into a diagnosis unless the technician actually states that diagnosis.
- If a source field is blank, keep the corresponding output blank. Do not invent content to fill it.
- Never invent measurements, test results, root causes, device states, parts, quantities, safety checks, customer statements, successful outcomes, or actions that were not provided.
- You may add neutral connective wording and professional framing such as "During inspection", "The reported issue was assessed", "The work carried out included", or "Following the stated intervention" only when it does not add a new factual claim.
- Preserve technical terminology and all concrete facts. Correct grammar, spelling and capitalization.
- Avoid vague filler, marketing language, and unsupported claims.
- Prefer concise paragraphs over bullet points.

Important: A short technician note should normally become a longer, more professional description, not the same sentence returned unchanged.

Return only one JSON object with exactly these string keys: diagnosis, work_done, parts. No markdown.`;
    const resp=await fetch("https://api.openai.com/v1/responses",{method:"POST",headers:{Authorization:`Bearer ${apiKey}`,"Content-Type":"application/json"},body:JSON.stringify({model,instructions,input:JSON.stringify(context),max_output_tokens:1400,store:false})});
    const payload=await resp.json().catch(()=>({}));const inTok=Number(payload?.usage?.input_tokens??0),outTok=Number(payload?.usage?.output_tokens??0);
    if(!resp.ok){if(usageEventId)await admin.rpc("complete_ai_usage",{p_event_id:usageEventId,p_status:"provider_error",p_input_tokens:inTok,p_output_tokens:outTok});return json({ok:false,configured:true,message:String(payload?.error?.message||`AI provider returned ${resp.status}`)},502);}
    const raw=extractOutputText(payload);if(!raw){if(usageEventId)await admin.rpc("complete_ai_usage",{p_event_id:usageEventId,p_status:"failed",p_input_tokens:inTok,p_output_tokens:outTok});return json({ok:false,configured:true,message:"AI provider returned an empty suggestion"},502);}
    let draft:any;try{draft=parseJsonText(raw);}catch{if(usageEventId)await admin.rpc("complete_ai_usage",{p_event_id:usageEventId,p_status:"failed",p_input_tokens:inTok,p_output_tokens:outTok});return json({ok:false,configured:true,message:"AI suggestion could not be parsed safely"},502);}
    if(usageEventId)await admin.rpc("complete_ai_usage",{p_event_id:usageEventId,p_status:"success",p_input_tokens:inTok,p_output_tokens:outTok});
    return json({ok:true,configured:true,draft:{diagnosis:text(draft?.diagnosis,6000),work_done:text(draft?.work_done,6000),parts:text(draft?.parts,4000)},usage:{...usage,used_this_month:claimedUsed,remaining:Math.max(monthlyLimit-claimedUsed,0),input_tokens:inputTokens+inTok,output_tokens:outputTokens+outTok}});
  }catch(e){return json({ok:false,message:e instanceof Error?e.message:String(e)},500);}
});
