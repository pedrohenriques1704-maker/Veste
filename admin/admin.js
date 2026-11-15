(() => {
"use strict";
const el=id=>document.getElementById(id), msg=t=>el("message").textContent=t;
const client=window.supabase.createClient("https://zodyzmeeossstkiwanqi.supabase.co","sb_publishable_26b9DoYuHezMJ06urxRk9w_qCE_TtlU",{auth:{storageKey:"veste-supabase-auth-v1",persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}});
const money=(n,c)=>{try{return Number(n).toLocaleString("pt-BR",{style:"currency",currency:c})}catch{return String(n)+" "+c}};
const date=s=>s?new Date(s).toLocaleString("pt-BR"):"—";
function table(id,headers,rows){const root=el(id);root.replaceChildren();const tab=document.createElement("table"),head=tab.createTHead().insertRow();headers.forEach(h=>{const c=document.createElement("th");c.textContent=h;head.append(c)});const body=tab.createTBody();for(const row of rows){const tr=body.insertRow();row.forEach(v=>tr.insertCell().textContent=v??"—")}root.append(tab)}
let revision=0;
function clear(){el("data").hidden=true;for(const id of ["accounts","catalog","available","shops","clicks","catalogDate"])el(id).textContent="—";for(const id of ["partners","daily","sync","financial"])el(id).replaceChildren()}
async function refresh(){
 const seq=++revision;clear();el("refresh").disabled=true;msg("Verificando acesso…");
 try{
 const {data:{session},error:sessionError}=await client.auth.getSession();if(seq!==revision)return;if(sessionError||!session){msg("Entre no VESTE com a sua conta administrativa e volte a esta página.");return}
 const {data:d,error}=await client.rpc("veste_admin_snapshot");if(seq!==revision)return;
 if(error||!d){msg(error?.code==="42501"?"Acesso restrito. Esta conta não possui permissão administrativa.":"Não foi possível consultar a operação. Verifique a instalação do backend.");return}
 for(const [id,value] of Object.entries({accounts:d.accounts,catalog:d.catalog,available:d.available,shops:d.shops,clicks:d.clicks30,catalogDate:date(d.last_catalog)}))el(id).textContent=value??"—";
 table("partners",["Parceiro","Produtos","Disponíveis","Última atualização"],(d.partners||[]).map(x=>[x.shop,x.products,x.available,date(x.synced_at)]));
 table("daily",["Data UTC","Acessos únicos por peça/minuto"],(d.daily_clicks||[]).map(x=>[x.day,x.clicks]));
 table("sync",["Processo","Horário","Resultado","Registros","Detalhe"],(d.sync||[]).map(x=>[x.kind,date(x.finished_at),x.ok?"OK":"Falhou",x.records,x.detail]));
 el("reportStatus").textContent=d.report_ready?"Relatório Awin importado. Apenas transações identificadas pelo VESTE; valores por moeda e status não equivalem a pagamento recebido.":"Relatório Awin ainda não importado. Não há dados financeiros verificados.";
 table("financial",["Parceiro","Moeda","Status","Transações","Conversões de venda","Vendas","Comissões"],(d.financial||[]).map(x=>[x.shop,x.currency,x.status,x.transactions,x.conversions,money(x.sales,x.currency),money(x.commissions,x.currency)]));
 el("data").hidden=false;msg("Acesso administrativo confirmado.");
 }catch{if(seq===revision)msg("Falha ao consultar o servidor.")}finally{if(seq===revision)el("refresh").disabled=false}
}
el("refresh").onclick=refresh;client.auth.onAuthStateChange((event)=>{if(event==="SIGNED_OUT"||event==="SIGNED_IN"||event==="USER_UPDATED"){revision++;clear();setTimeout(refresh,0)}});refresh();
})();