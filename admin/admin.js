(() => {
"use strict";
const el=id=>document.getElementById(id),put=(id,value)=>el(id).textContent=value??"—",msg=t=>put("message",t);
if(!window.supabase?.createClient){msg("Biblioteca de autenticação indisponível. Recarregue a página.");el("refresh").onclick=()=>location.reload();return}
const client=window.supabase.createClient("https://zodyzmeeossstkiwanqi.supabase.co","sb_publishable_26b9DoYuHezMJ06urxRk9w_qCE_TtlU",{auth:{storageKey:"veste-supabase-auth-v1",persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}});
const labels={home:"Hoje",closet:"Meu closet",looks:"Looks",week:"Planejar",discover:"Descobrir",style:"Perfil"};
const number=n=>n==null?"—":Number(n).toLocaleString("pt-BR",{maximumFractionDigits:1});
const percent=(a,b)=>b?number(a/b*100)+"%":"—";
const money=(n,c)=>{try{return Number(n).toLocaleString("pt-BR",{style:"currency",currency:c})}catch{return String(n)+" "+c}};
const date=s=>s?new Date(s).toLocaleString("pt-BR",{timeZone:"America/Sao_Paulo"}):"—";
const shortDay=s=>String(s||"").slice(5,10).split("-").reverse().join("/");
function node(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n}
function empty(root,message){root.replaceChildren(node("div",message,"chart-empty"))}
function table(id,headers,rows){const root=el(id);root.replaceChildren();if(!rows.length){root.append(node("p","Nenhum registro disponível.","small"));return}const tab=document.createElement("table"),head=tab.createTHead().insertRow();headers.forEach(h=>{const c=node("th",h);c.scope="col";head.append(c)});const body=tab.createTBody();for(const row of rows){const tr=body.insertRow();row.forEach(v=>tr.insertCell().textContent=v??"—")}root.append(tab)}
function rank(id,rows){const root=el(id);root.replaceChildren();if(!rows.length){empty(root,"Sem dados para este período.");return}for(const x of rows){const row=node("div",null,"rank-row"),line=node("div",null,"rank-label");line.append(node("span",x.label),node("small",x.detail));const track=node("div",null,"track"),fill=node("div",null,"fill");fill.style.width=Math.max(0,Math.min(100,x.share||0))+"%";track.append(fill);track.setAttribute("aria-hidden","true");row.append(line,track);root.append(row)}}
const NS="http://www.w3.org/2000/svg";
function svg(tag,attrs={},text){const n=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!=null)n.textContent=text;return n}
function chart(id,rows,field,label){
 const root=el(id);root.replaceChildren();const values=rows.map(v=>Math.max(0,Number(v[field])||0));if(!rows.length||!values.some(Boolean)){empty(root,"Ainda não há "+label.toLowerCase()+" registrados neste período.");return}
 const w=580,h=220,left=40,right=14,top=15,bottom=32,span=w-left-right,height=h-top-bottom,maximum=Math.max(...values),step=Math.max(1,Math.ceil(maximum/4)),max=step*4,x=i=>rows.length===1?left+span/2:left+i*span/(rows.length-1),y=v=>top+height-v/max*height;
 const g=svg("svg",{viewBox:"0 0 "+w+" "+h,role:"img","aria-label":label+" por dia"});for(let i=0;i<=4;i++){let v=i*step;g.append(svg("line",{x1:left,x2:w-right,y1:y(v),y2:y(v),stroke:"#e7ded5","stroke-dasharray":"3 4"}),svg("text",{x:left-8,y:y(v)+4,"text-anchor":"end",fill:"#766a5e","font-size":11},number(v)))}
 const pts=values.map((v,i)=>[x(i),y(v)]),line=pts.map(([a,b],i)=>(i?"L":"M")+a+" "+b).join(" ");
 if(rows.length>1)g.append(svg("path",{d:"M"+pts[0][0]+" "+y(0)+" "+line.replace(/^M/,"L")+" L"+pts.at(-1)[0]+" "+y(0)+" Z",fill:"#a78068","fill-opacity":.13}),svg("path",{d:line,fill:"none",stroke:"#956f59","stroke-width":2.5,"stroke-linecap":"round","stroke-linejoin":"round"}));
 pts.forEach(([a,b],i)=>{const point=svg("circle",{cx:a,cy:b,r:rows.length>35?2.5:4,fill:"#79513d",stroke:"#fffdf9","stroke-width":1.3});point.append(svg("title",{},shortDay(rows[i].day)+": "+number(values[i])));g.append(point)});
 const marks=[...new Set([0,Math.floor((rows.length-1)/4),Math.floor((rows.length-1)/2),Math.floor((rows.length-1)*.75),rows.length-1])];for(const i of marks)g.append(svg("text",{x:x(i),y:h-8,"text-anchor":i===0&&rows.length>1?"start":i===rows.length-1&&rows.length>1?"end":"middle",fill:"#766a5e","font-size":11},shortDay(rows[i].day)));root.append(g);
}
let revision=0,usage=null;
function renderUsage(d){
 usage=d;const counts={sessions:d.sessions,activeUsers:d.users,views:d.views,newAccounts:d.new_accounts,todayUsers:d.today_users,users7:d.users7,users30:d.users30,depth:d.sessions?d.views/d.sessions:null,returning:d.returning_users};Object.entries(counts).forEach(([k,v])=>put(k,number(v)));put("usagePeriod",d.period_days+" dias");
 put("trackingStatus","Coleta iniciada em "+date(d.started_at)+". Somente navegação autenticada de quem autorizou estatísticas; não há histórico retroativo. Hoje é um dia parcial.");
 const pages=d.pages||[];rank("pageRank",pages.map(x=>({label:labels[x.page]||x.page,detail:number(x.views)+" · "+percent(x.views,d.views),share:d.views?x.views/d.views*100:0})));
 table("pageTable",["Página","Visualizações","Participação","Usuários","Sessões"],pages.map(x=>[labels[x.page]||x.page,number(x.views),percent(x.views,d.views),number(x.users),number(x.sessions)]));
 table("dailyUsage",["Dia","Sessões","Usuários","Visualizações"],(d.daily||[]).map(x=>[shortDay(x.day),number(x.sessions),number(x.users),number(x.views)]));renderActivity();
}
function renderActivity(){const field=el("chartMetric").value;if(usage)chart("activityChart",usage.daily||[],field,{sessions:"Sessões",users:"Usuários ativos",views:"Visualizações"}[field])}
function finance(d){const root=el("financialCards");root.replaceChildren();if(!d.report_ready){put("reportStatus","Relatório Awin ainda não importado. Não há dados financeiros verificados.");return}put("reportStatus","Somente transações atribuídas ao VESTE. Comissões por moeda e status, não equivalem a pagamentos recebidos.");
 const map=new Map();for(const x of d.financial||[]){const k=x.currency;const a=map.get(k)||{sales:0,commissions:0,conversions:0};if(["approved","confirmed","pending"].includes(String(x.status).toLowerCase())){a.sales+=Number(x.sales)||0;a.commissions+=Number(x.commissions)||0;a.conversions+=Number(x.conversions)||0;}map.set(k,a)}
 if(!map.size){root.append(node("p","Nenhuma transação atribuída ao VESTE no período.","small"));return}for(const [c,a] of map){for(const [label,value] of [["Conversões ("+c+")",number(a.conversions)],["Vendas pendentes/aprovadas",money(a.sales,c)],["Comissões pendentes/aprovadas",money(a.commissions,c)]]){const card=node("article");card.append(node("span",label),node("strong",value));root.append(card)}}}
function syncStatus(id,dateId,row){put(id,row?(row.ok?"Sincronizado":"Falha na última execução"):"Sem execução");el(id).dataset.state=row?(row.ok?"ok":"error"):"";put(dateId,row?date(row.finished_at)+" · "+number(row.records)+" registros":"Nenhum histórico registrado.")}
function commerce(d){for(const [k,v] of Object.entries({accounts:number(d.accounts),catalog:number(d.catalog),available:number(d.available),shops:number(d.shops),clicks:number(d.clicks30),catalogDate:date(d.last_catalog)}))put(k,v);
 const partners=d.partners||[];rank("partnerRank",partners.map(x=>({label:x.shop||"Parceiro",detail:number(x.available)+" / "+number(x.products),share:x.products?x.available/x.products*100:0})));
 const recorded=new Map((d.daily_clicks||[]).map(x=>[x.day,x.clicks]));const days=Array.from({length:30},(_,i)=>{const d=new Date();d.setUTCDate(d.getUTCDate()-29+i);const day=d.toISOString().slice(0,10);return {day,clicks:recorded.get(day)||0}});chart("clickChart",days,"clicks","Visitas a ofertas");
 table("partners",["Parceiro","Produtos","Disponíveis","Acessos · 30d","Última atualização"],partners.map(x=>[x.shop,number(x.products),number(x.available),number(x.clicks30),date(x.synced_at)]));
 finance(d);table("financial",["Parceiro","Moeda","Status","Transações","Conversões","Vendas","Comissões"],(d.financial||[]).map(x=>[x.shop,x.currency,x.status,number(x.transactions),number(x.conversions),money(x.sales,x.currency),money(x.commissions,x.currency)]));
 const runs=d.sync||[];syncStatus("catalogSync","catalogSyncDate",runs.find(x=>x.kind==="catalog"));syncStatus("transactionSync","transactionSyncDate",runs.find(x=>x.kind==="transactions"));
 table("sync",["Processo","Horário","Resultado","Registros","Detalhe"],runs.map(x=>[x.kind,date(x.finished_at),x.ok?"OK":"Falhou",number(x.records),x.detail]));
}
function roster(rows){put("adminCount",number(rows.length)+" "+(rows.length===1?"conta":"contas"));table("adminRoster",["Conta autorizada","Tipo de acesso","Último login","Cadastro"],rows.map(x=>[(x.email||"Conta sem e-mail")+(x.current_account?" · Você":""),"Administrador",date(x.last_sign_in_at),date(x.created_at)]))}
const clear=()=>{usage=null;el("data").hidden=true;el("sections").hidden=true;for(const id of ["activityChart","pageRank","pageTable","dailyUsage","partnerRank","clickChart","partners","financial","financialCards","sync","adminRoster"])el(id).replaceChildren();for(const id of ["sessions","activeUsers","views","accounts","newAccounts","todayUsers","users7","users30","depth","returning","catalog","available","shops","clicks","catalogDate","adminCount","catalogSync","transactionSync","catalogSyncDate","transactionSyncDate","trackingStatus","reportStatus"])put(id,"—")};
async function refresh(){const seq=++revision;clear();el("refresh").disabled=true;msg("Verificando acesso…");try{
 const {data:{session},error:sessionError}=await client.auth.getSession();if(seq!==revision)return;if(sessionError||!session){msg("Entre no VESTE com a sua conta administrativa e volte a esta página.");return}
 const [business,product,access]=await Promise.all([client.rpc("veste_admin_snapshot"),client.rpc("veste_admin_usage_snapshot",{period_days:Number(el("period").value)}),client.rpc("veste_admin_access_roster")]);if(seq!==revision)return;
 const errors=[business.error,product.error,access.error].filter(Boolean);if(errors.length||!business.data||!product.data||!Array.isArray(access.data)){msg(errors.some(e=>e.code==="42501")?"Acesso restrito. Esta conta não possui permissão administrativa.":"Não foi possível consultar o painel. Verifique a instalação do backend.");return}
 commerce(business.data);renderUsage(product.data);roster(access.data);el("data").hidden=false;el("sections").hidden=false;msg("Dados atualizados às "+date(new Date().toISOString()));
 }catch{if(seq===revision)msg("Falha ao consultar o servidor.")}finally{if(seq===revision)el("refresh").disabled=false}}
el("refresh").onclick=refresh;el("period").onchange=refresh;el("chartMetric").onchange=renderActivity;
client.auth.onAuthStateChange(event=>{if(event==="SIGNED_OUT"||event==="SIGNED_IN"||event==="USER_UPDATED"){revision++;clear();setTimeout(refresh,0)}});refresh();
})();