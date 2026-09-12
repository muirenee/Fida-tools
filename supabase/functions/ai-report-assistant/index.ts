import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json"}});
const text=(v:unknown,max=5000)=>String(v??"").trim().slice(0,max);

const extractOutputText=(payload:any)=>{
  if(typeof payload?.output_text==="string"&&payload.output_text.trim())return payload.output_text.trim();
  let out="";
  for(const item of Array.isArray(payload?.output)?payload.output:[]){
    if(item?.type!=="message"||!Array.isArray(item?.content))continue;
    for(const part of item.content){if(part?.type==="output_text"&&typeof part?.text==="string")out+=part.text;}
  }
  return out.trim();
};

const parseJsonText=(raw:string)=>{
  let v=raw.trim();
  if(v.startsWith("```"))v=v.replace(/^```(?:json)?\s*/i,"").replace(/\s*```$/i,"").trim();
  return JSON.parse(v);
};

Deno.serve(async(req:Request)=>{
  if(req.method!=="POST")return json({ok:false,message:"Method not allowed"},405);
  try{
    const auth=req.headers.get("Authorization")??"";const jwt=auth.startsWith("Bearer ")?auth.slice(7):"";
    if(!jwt)return json({ok:false,message:"Authentication required"},401);
    const admin=createClient(Deno.env.get("SUPABASE_URL")!,Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:userData,error:userError}=await admin.auth.getUser(jwt);const user=userData?.user;
    if(userError||!user)return json({ok:false,message:"Invalid session"},401);
    const body=await req.json().catch(()=>({}));const workspaceId=text(body?.workspace_id,80);
    if(!workspaceId)return json({ok:false,message:"Workspace is required"},400);
    const {data:member}=await admin.from("workspace_members").select("status").eq("workspace_id",workspaceId).eq("user_id",user.id).maybeSingle();
    if(String(member?.status??"").toLowerCase()!=="active")return json({ok:false,message:"Active workspace access required"},403);

    const apiKey=Deno.env.get("OPENAI_API_KEY")??"";
    if(!apiKey)return json({ok:false,configured:false,message:"AI report assistant is not configured yet."},503);
    const model=Deno.env.get("OPENAI_MODEL")||"gpt-5.6-luna";
    const context={title:text(body?.title,500),reported_problem:text(body?.problem,5000),diagnosis_notes:text(body?.diagnosis,5000),work_notes:text(body?.work_done,5000),parts_materials:text(body?.parts,3000)};
    if(!context.reported_problem&&!context.diagnosis_notes&&!context.work_notes&&!context.parts_materials)return json({ok:false,message:"Enter some service notes before using AI assist."},400);

    const instructions=`You are a field-service report writing assistant. Improve technician notes into concise professional service-report wording. Never invent facts, measurements, tests, faults, parts, quantities, outcomes, safety checks, or actions that are not present in the input. Preserve technical meaning. If a field has insufficient factual information, return the original text for that field or an empty string. Do not include customer names or assumptions. Return only one JSON object with exactly these string keys: diagnosis, work_done, parts. No markdown.`;
    const resp=await fetch("https://api.openai.com/v1/responses",{method:"POST",headers:{Authorization:`Bearer ${apiKey}`,"Content-Type":"application/json"},body:JSON.stringify({model,instructions,input:JSON.stringify(context),max_output_tokens:1000,store:false})});
    const payload=await resp.json().catch(()=>({}));
    if(!resp.ok)return json({ok:false,configured:true,message:String(payload?.error?.message||`AI provider returned ${resp.status}`)},502);
    const raw=extractOutputText(payload);if(!raw)return json({ok:false,configured:true,message:"AI provider returned an empty suggestion"},502);
    let draft:any;try{draft=parseJsonText(raw);}catch{return json({ok:false,configured:true,message:"AI suggestion could not be parsed safely"},502);}
    return json({ok:true,configured:true,draft:{diagnosis:text(draft?.diagnosis,6000),work_done:text(draft?.work_done,6000),parts:text(draft?.parts,4000)}});
  }catch(e){return json({ok:false,message:e instanceof Error?e.message:String(e)},500);}
});
