#!/usr/bin/env python3
"""Scheduled, server-only Awin ingestion. Standard library; never logs secrets."""
import csv, gzip, io, json, os, re, sys, unicodedata, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

def text(x, limit=180):
    return ("" if x is None else str(x)).strip()[:limit]
def norm(x):
    return "".join(c for c in unicodedata.normalize("NFD", text(x, 2000).lower()) if unicodedata.category(c)!="Mn")
def https(x, host=None):
    u=urllib.parse.urlsplit(text(x, 3000))
    if u.scheme!="https" or not u.hostname or u.username or u.password or (host and u.hostname not in host): return ""
    return u.geturl()
def amount(v, signed=False):
    s=text(v,40).replace("BRL","").replace("R$","").strip()
    if "," in s: s=s.replace(".","").replace(",",".")
    try:
        n=Decimal(s)
        if n.is_finite() and (-100000 if signed else 0)<=n<=100000: return float(n)
    except InvalidOperation: pass
    return None
def get(url):
    if not https(url,{"productdata.awin.com","ui.awin.com","api.awin.com"}): raise ValueError("Untrusted feed host")
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"VESTE-Catalog/7.3"}),timeout=90) as r:
        if not https(r.geturl(),{"productdata.awin.com","ui.awin.com","api.awin.com"}): raise ValueError("Unexpected feed host")
        data=r.read(50*1024*1024+1)
    if len(data)>50*1024*1024: raise ValueError("Feed too large")
    if data[:2]==b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as z: data=z.read(100*1024*1024+1)
    if len(data)>100*1024*1024: raise ValueError("Feed too large")
    return data
def db(path,payload=None):
    base=os.environ["SUPABASE_URL"].rstrip("/")
    if not https(base,{"zodyzmeeossstkiwanqi.supabase.co"}): raise ValueError("Invalid Supabase host")
    key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    req=urllib.request.Request(base+"/rest/v1/"+path,data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode(),headers={"apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json","Prefer":"return=minimal,resolution=merge-duplicates"})
    with urllib.request.urlopen(req,timeout=90) as r:
        b=r.read(); return json.loads(b) if b else None
def log(kind,ok,n,detail):
    db("rpc/veste_commerce_sync_log",dict(sync_kind=kind,success=ok,record_count=n,summary=detail))
class SyncIssue(Exception):
    """Only constant diagnostic codes or numeric counters may be shown in logs."""
    def __init__(self, code): self.code=code; super().__init__(code)

def field_key(key):
    return re.sub(r"[^a-z0-9]+","_",norm(key)).strip("_")

def rows(data):
    try:
        sample=data.decode("utf-8-sig",errors="strict")
        header=sample.splitlines()[0] if sample else ""
        # Identify delimiter on the header alone, not a truncated sample containing
        # quoted multiline product descriptions (Sniffer can fail on such files).
        delimiters=[(",",len(next(csv.reader([header],delimiter=",")))),(";",len(next(csv.reader([header],delimiter=";")))),("\t",len(next(csv.reader([header],delimiter="\t"))))]
        delim,width=max(delimiters,key=lambda x:x[1])
        if width<2: raise SyncIssue("csv_header_not_recognized")
        reader=csv.DictReader(io.StringIO(sample,newline=""),delimiter=delim,strict=True)
        keys=[field_key(x) for x in reader.fieldnames or []]
        if not all(keys) or len(set(keys))!=len(keys): raise SyncIssue("csv_duplicate_or_empty_columns")
        result=[]
        for row in reader:
            if None in row or any(v is None for v in row.values()): raise SyncIssue("csv_incomplete_row")
            result.append({field_key(k):v for k,v in row.items()})
        return result
    except (UnicodeDecodeError,csv.Error): raise SyncIssue("csv_invalid_encoding_or_quoting") from None

def request_stage(url,code):
    try: return get(url)
    except urllib.error.HTTPError as e: raise SyncIssue(code+"_http_"+str(e.code)) from None
    except SyncIssue: raise
    except Exception: raise SyncIssue(code+"_download_failed") from None

def pick_field(row,*keys):
    return next((row[k] for k in keys if row.get(k) not in ("",None)), "")

def select_feeds(data,allowed,confirmed=None):
    parsed=rows(data)
    if not parsed: raise SyncIssue("feed_list_empty")
    if not any(k in parsed[0] for k in ("advertiser_id","merchant_id","merchantid")): raise SyncIssue("feed_list_missing_advertiser_column")
    candidates={}; target_count=0; status_set=set(); format_set=set()
    for r in parsed:
        merchant=text(pick_field(r,"advertiser_id","merchant_id","merchantid"),20)
        if not merchant.isdigit() or int(merchant) not in allowed: continue
        target_count+=1
        status=norm(pick_field(r,"membership_status","relationship","membership"))
        fmt=norm(pick_field(r,"datafeed_format","data_feed_format","feed_format","format"))
        status_set.add(status if status in ("active","joined","approved","yes","pending","suspended","rejected","notjoined","not joined","inactive","") else "other")
        format_set.add(fmt if fmt in ("awin","legacy","standard","google","enhanced","") else "other")
        if status not in ("active","joined","approved","yes") and not (confirmed and int(merchant) in confirmed and status not in ("suspended","rejected","inactive","pending")): continue
        if fmt not in ("awin","legacy","standard",""): continue
        language=norm(pick_field(r,"language","feed_language"))
        region=norm(pick_field(r,"primary_region","region"))
        candidates.setdefault(int(merchant),[]).append((r,language,region))
    chosen={}
    for mid,options in candidates.items():
        preferred=[x for x in options if x[1] in ("portuguese","portugues","portuguese (brazil)","pt","pt_br","pt-br") and x[2] in ("","br","brazil","brasil")]
        pool=preferred or options
        if len(pool)!=1: raise SyncIssue("multiple_legacy_feeds_for_"+str(mid))
        chosen[mid]=pool[0][0]
    print(f"feed_list rows={len(parsed)} target_rows={target_count} status={sorted(status_set)} formats={sorted(format_set)} chosen={len(chosen)}",flush=True)
    return chosen

GROUPS=[("onepiece",r"\b(vestido|macacao|macaquinho|dress)\b"),("shoes",r"\b(tenis|sapato|bota|coturno|mocassim|sandalia|chinelo|sapatilha|chuteira|sneaker)\b"),("accessory",r"\b(bolsa|mochila|cinto|bone|oculos|colar|brinco|relogio|meia|viseira)\b"),("layer",r"\b(jaqueta|blazer|casaco|colete|cardigan|parka|sobretudo)\b"),("bottom",r"\b(calca|shorts?|bermuda|saia|legging|jogger)\b"),("top",r"\b(camisa|camiseta|regata|blusa|polo|moletom|cropped|sueter|top)\b")]
COLORS={"azul marinho":"marinho","azul-marinho":"marinho","marinho":"marinho","off white":"offwhite","off-white":"offwhite","offwhite":"offwhite","verde oliva":"oliva","oliva":"oliva","preto":"preto","preta":"preto","branco":"branco","branca":"branco","cinza":"cinza","bege":"bege","caramelo":"caramelo","marrom":"marrom","azul":"azul","verde":"verde","vermelho":"vermelho","vermelha":"vermelho","rosa":"rosa","vinho":"vinho","amarelo":"amarelo","amarela":"amarelo","roxo":"roxo","roxa":"roxo","laranja":"laranja","jeans":"jeans"}
def normalize(r,merchant,shop,stamp):
    def pick(*keys): return pick_field(r,*keys)
    name=text(pick("product_name","title","name"))
    category=text(pick("merchant_category","product_type","category_name"),300)
    group=next((k for k,rx in GROUPS if re.search(rx,norm(name))),None) or next((k for k,rx in GROUPS if re.search(rx,norm(category))),None)
    variant=text(pick("merchant_product_id","id"),180)
    base=text(pick("item_group_id","parent_product_id","product_group_id") or variant,180)
    merchant_url=https(pick("merchant_deep_link","merchant_url","product_url"))
    if merchant==118977:
        slug=re.fullmatch(r"/([a-z0-9-]+)/p/?",urllib.parse.urlsplit(merchant_url).path)
        if slug and urllib.parse.urlsplit(merchant_url).hostname in {"www.lauriesporte.com.br","lauriesporte.com.br"}: base=slug.group(1)
        else: return None  # Preserve the original Lauri stable product-ID scheme.
    link=https(pick("aw_deep_link","awin_deep_link","affiliate_url","link"))
    # Only accept Awin tracking URLs, not merchant links masquerading as affiliate URLs.
    if not link or urllib.parse.urlsplit(link).hostname not in {"www.awin1.com","awin1.com","www.zenaps.com","zenaps.com"}: return None
    if not name or not group or not base: return None
    raw=text(pick("colour","color","product_colour"),100); c=norm(raw or name)
    color=next((v for k,v in COLORS.items() if re.search(r"\b"+re.escape(k)+r"\b",c)),"")
    gender=norm(pick("gender","audience","product_gender") or name)
    audience="feminino" if re.search(r"\b(feminino|feminina|female|women)\b",gender) else "masculino" if re.search(r"\b(masculino|masculina|male|men)\b",gender) else "unissex" if "unisex" in gender or "unissex" in gender else ""
    cur=text(pick("currency","currency_code") or "BRL",10).upper()
    raw_price=pick("search_price","store_price","price")
    if " BRL" in str(raw_price): cur="BRL"
    price=amount(raw_price) if cur in ("BRL","R$") else None
    stock=norm(pick("in_stock","availability","stock_status")); sale=norm(pick("is_for_sale"))
    # Unknown stock is not promoted as available.
    available=stock in ("1","true","yes","y","sim","in stock","in_stock","available","disponivel","instock")
    on_sale=sale not in ("0","false","no","n","nao")
    size=text(pick("size","size_name","product_size"),40)
    return dict(id=f"awin:{merchant}:{base}",source="awin",merchant_id=merchant,merchant_product_id=base,awin_product_id=text(pick("aw_product_id"),100),name=name,description=text(pick("description","product_short_description"),1000),affiliate_url=link,merchant_url=merchant_url,image_url=https(pick("aw_image_url","merchant_image_url","image_link")),price=price,rrp_price=amount(pick("rrp_price","rrp")) if cur in ("BRL","R$") else None,currency="BRL" if cur in ("BRL","R$") else cur,group_key=group,merchant_category=category,category_name=text(pick("category_name"),180),brand=text(pick("brand_name","brand"),80),shop=shop,color=color,raw_colour=raw,audience=audience,sizes=[size] if size else [],in_stock=available,is_for_sale=on_sale,variant_count=1,source_updated_at=stamp,synced_at=datetime.now(timezone.utc).isoformat())
def combine(items):
    out={}
    for x in items:
        if x is None: continue
        prev=out.get(x["id"])
        if prev:
            # Lowest priced available variant, never an unavailable one when availability is known.
            good=lambda p:p["in_stock"] and p["is_for_sale"]
            choose=x if (good(x) and not good(prev)) or (good(x)==good(prev) and x["price"] is not None and (prev["price"] is None or x["price"]<prev["price"])) else prev
            sizes=sorted(set((prev["sizes"] if good(prev) else [])+(x["sizes"] if good(x) else [])))
            count=prev["variant_count"]+1
            out[x["id"]]={**choose,"sizes":sizes,"variant_count":count}
        else: out[x["id"]]=x
    return list(out.values())
def sync_catalog():
    publisher=os.environ["AWIN_PUBLISHER_ID"].strip()
    key=os.environ["AWIN_FEED_KEY"].strip()
    allowed={int(x) for x in os.environ.get("AWIN_MERCHANT_IDS","118977").split(",") if x.strip()}
    if not publisher.isdigit() or not key or not allowed: raise SyncIssue("catalog_config_missing")
    encoded=urllib.parse.quote(key,safe="")
    urls=[
        ("feed_list",f"https://ui.awin.com/productdata-darwin-download/publisher/{publisher}/{encoded}/1/feedList"),
        # Awin documents this endpoint as the fallback for legacy-only lists.
        ("legacy_list",f"https://productdata.awin.com/datafeed/list/apikey/{encoded}")
    ]
    selected={}; last_code="feed_list_no_approved_legacy"; confirmed=set()
    try:
        params=urllib.parse.urlencode({"relationship":"joined","countryCode":"BR","accessToken":os.environ["AWIN_API_TOKEN"]})
        programmes=json.loads(request_stage(f"https://api.awin.com/publishers/{publisher}/programmes?"+params,"programmes"))
        if isinstance(programmes,list): confirmed={int(x["id"]) for x in programmes if isinstance(x,dict) and str(x.get("id","")).isdigit()}&allowed
        print(f"programme membership confirmed={len(confirmed)} expected={len(allowed)}",flush=True)
    except Exception: print("programme membership check unavailable",flush=True)
    for stage,url in urls:
        try:
            selected=select_feeds(request_stage(url,stage),allowed,confirmed)
            if set(selected)==allowed: break
            last_code=stage+"_no_approved_legacy"
        except SyncIssue as e: last_code=stage+"_"+e.code
    if set(selected)!=allowed: raise SyncIssue(last_code+("_joined" if confirmed==allowed else "_membership_unconfirmed"))
    total=0
    for mid,r in selected.items():
        feed=https(pick_field(r,"url","download_url","feed_url"),{"productdata.awin.com","ui.awin.com"})
        if not feed: raise SyncIssue("feed_invalid_download_url")
        stamp=text(pick_field(r,"last_imported","last_updated","last_update"),40)
        try:
            parsed_stamp=datetime.fromisoformat(stamp.replace("Z","+00:00"))
            if parsed_stamp.tzinfo is None: parsed_stamp=parsed_stamp.replace(tzinfo=timezone.utc)
            stamp=parsed_stamp.isoformat()
        except ValueError: raise SyncIssue("feed_invalid_source_timestamp") from None
        parsed=rows(request_stage(feed,"product_feed"))
        if not parsed: raise SyncIssue("product_feed_empty")
        products=combine(normalize(x,mid,text(pick_field(r,"advertiser_name","merchant_name"),80),stamp) for x in parsed)
        available=sum(p["in_stock"] and p["is_for_sale"] for p in products)
        variants=sum(p["variant_count"] for p in products)
        print(f"catalog merchant={mid} rows={len(parsed)} accepted_variants={variants} products={len(products)} available={available}",flush=True)
        if not products: raise SyncIssue("product_feed_no_supported_rows")
        if not available: raise SyncIssue("product_feed_no_available_rows")
        if variants < len(parsed)*.7: raise SyncIssue("product_feed_coverage_below_70_percent")
        # Keep the existing atomic database coverage, identity and staleness guards.
        try: db("rpc/veste_catalog_snapshot_import",{"merchant":mid,"records":products,"expected_rows":len(parsed)})
        except urllib.error.HTTPError as e:
            # Only known database exception phrases are permitted; never log response bodies.
            try: reason=json.loads(e.read().decode()).get("message","")
            except Exception: reason=""
            codes={"Catalog identity/coverage mismatch":"db_identity_coverage_mismatch","Feed older than existing catalog":"db_feed_older","Incomplete or unsupported feed":"db_incomplete_feed","Invalid catalog batch":"db_invalid_batch","Invalid catalog row":"db_invalid_row"}
            raise SyncIssue(codes.get(reason,"db_import_http_"+str(e.code))) from None
        total+=len(products)
    log("catalog",True,total,"Approved Awin legacy feeds imported; stock validated")
def sync_transactions():
    pub=os.environ["AWIN_PUBLISHER_ID"]; token=os.environ["AWIN_API_TOKEN"]
    if not pub.isdigit() or not token: raise ValueError("Missing transaction config")
    now=datetime.now(timezone.utc); start=now-timedelta(days=30)
    params={"startDate":start.strftime("%Y-%m-%dT%H:%M:%S"),"endDate":now.strftime("%Y-%m-%dT%H:%M:%S"),"timezone":"UTC","dateType":"transaction","accessToken":token}
    data=json.loads(get(f"https://api.awin.com/publishers/{pub}/transactions/?"+urllib.parse.urlencode(params)))
    if not isinstance(data,list): raise ValueError("Unexpected transaction response")
    records=[]
    for x in data:
        refs=x.get("clickRefs") or {}
        ref=x.get("clickRef") or (refs.get("clickRef") if isinstance(refs,dict) else "")
        # Ignore other publisher traffic; never import customer/order identifiers.
        if ref!="veste-app": continue
        sale=x.get("saleAmount") or {}; commission=x.get("commissionAmount") or {}
        if not isinstance(sale,dict) or not isinstance(commission,dict): raise ValueError("Unexpected monetary format")
        cur=text(commission.get("currency"),3)
        if not cur or cur!=text(sale.get("currency"),3): raise ValueError("Currency mismatch")
        sv=amount(sale.get("amount"),signed=True); cv=amount(commission.get("amount"),signed=True)
        if sv is None or cv is None or not x.get("id") or not x.get("transactionDate"): raise ValueError("Invalid transaction")
        stamp=datetime.fromisoformat(str(x["transactionDate"]).replace("Z","+00:00"))
        if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
        records.append(dict(id=str(x["id"]),merchant_id=x.get("advertiserId"),transaction_at=stamp.isoformat(),status=text(x.get("commissionStatus"),30),currency=cur,sale_amount=sv,commission_amount=cv,attributed=True,transaction_type=text(x.get("type"),60)))
    for i in range(0,len(records),200): db("rpc/veste_commerce_transactions_import",{"records":records[i:i+200]})
    log("transactions",True,len(records),"30-day Awin publisher report; grouped by status/currency")
def main():
    failed=False
    for kind,fn in [("catalog",sync_catalog),("transactions",sync_transactions)]:
        try: fn(); print(kind+": OK")
        except Exception as exc:
            failed=True; detail=exc.code if isinstance(exc,SyncIssue) else type(exc).__name__+": sync not completed"
            print(kind+": "+detail,file=sys.stderr)
            try: log(kind,False,0,detail)
            except Exception: pass
    return int(failed)
if __name__=="__main__": raise SystemExit(main())
