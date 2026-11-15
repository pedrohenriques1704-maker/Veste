#!/usr/bin/env python3
"""Scheduled, server-only Awin ingestion. Standard library; never logs secrets."""
import csv, gzip, io, json, os, re, sys, unicodedata, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

def text(x, limit=180):
    return str(x or "").strip()[:limit]
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
def rows(data):
    sample=data.decode("utf-8-sig",errors="strict")
    dialect=csv.Sniffer().sniff(sample[:8192],delimiters=",;\t")
    return list(csv.DictReader(io.StringIO(sample),dialect=dialect))
GROUPS=[("onepiece",r"\b(vestido|macacao|macaquinho|dress)\b"),("shoes",r"\b(tenis|sapato|bota|coturno|mocassim|sandalia|chinelo|sapatilha|chuteira|sneaker)\b"),("accessory",r"\b(bolsa|mochila|cinto|bone|oculos|colar|brinco|relogio|meia|viseira)\b"),("layer",r"\b(jaqueta|blazer|casaco|colete|cardigan|parka|sobretudo)\b"),("bottom",r"\b(calca|shorts?|bermuda|saia|legging|jogger)\b"),("top",r"\b(camisa|camiseta|regata|blusa|polo|moletom|cropped|sueter|top)\b")]
COLORS={"azul marinho":"marinho","azul-marinho":"marinho","marinho":"marinho","off white":"offwhite","off-white":"offwhite","offwhite":"offwhite","verde oliva":"oliva","oliva":"oliva","preto":"preto","preta":"preto","branco":"branco","branca":"branco","cinza":"cinza","bege":"bege","caramelo":"caramelo","marrom":"marrom","azul":"azul","verde":"verde","vermelho":"vermelho","vermelha":"vermelho","rosa":"rosa","vinho":"vinho","amarelo":"amarelo","amarela":"amarelo","roxo":"roxo","roxa":"roxo","laranja":"laranja","jeans":"jeans"}
def normalize(r,merchant,shop,stamp):
    def pick(*keys): return next((r[k] for k in keys if r.get(k)), "")
    name=text(pick("product_name","title","name"))
    category=text(pick("merchant_category","product_type","category_name"),300)
    group=next((k for k,rx in GROUPS if re.search(rx,norm(name))),None) or next((k for k,rx in GROUPS if re.search(rx,norm(category))),None)
    variant=text(pick("merchant_product_id","id"),180)
    base=text(pick("item_group_id","product_group_id") or variant,180)
    merchant_url=https(pick("merchant_deep_link"))
    if merchant==118977:
        slug=re.fullmatch(r"/([a-z0-9-]+)/p/?",urllib.parse.urlsplit(merchant_url).path)
        if slug: base=slug.group(1)
        else: return None  # Preserve the original Lauri stable product-ID scheme.
    link=https(pick("aw_deep_link","affiliate_url","link"))
    # Only accept Awin tracking URLs, not merchant links masquerading as affiliate URLs.
    if not link or urllib.parse.urlsplit(link).hostname not in {"www.awin1.com","awin1.com","www.zenaps.com","zenaps.com"}: return None
    if not name or not group or not base: return None
    raw=text(pick("colour","color"),100); c=norm(raw or name)
    color=next((v for k,v in COLORS.items() if re.search(r"\b"+re.escape(k)+r"\b",c)),"")
    gender=norm(pick("gender","audience") or name)
    audience="feminino" if re.search(r"\b(feminino|feminina|female|women)\b",gender) else "masculino" if re.search(r"\b(masculino|masculina|male|men)\b",gender) else "unissex" if "unisex" in gender or "unissex" in gender else ""
    cur=text(pick("currency","currency_code") or "BRL",10).upper()
    raw_price=pick("search_price","store_price","price")
    if " BRL" in str(raw_price): cur="BRL"
    price=amount(raw_price) if cur in ("BRL","R$") else None
    stock=norm(pick("in_stock","availability","stock_status")); sale=norm(pick("is_for_sale"))
    # Unknown stock is not promoted as available.
    available=stock in ("1","true","yes","in stock","in_stock","available","disponivel","instock")
    on_sale=sale not in ("0","false","no")
    size=text(pick("size","size_name"),40)
    return dict(id=f"awin:{merchant}:{base}",source="awin",merchant_id=merchant,merchant_product_id=base,awin_product_id=text(pick("aw_product_id"),100),name=name,description=text(pick("description"),1000),affiliate_url=link,merchant_url=merchant_url,image_url=https(pick("aw_image_url","merchant_image_url","image_link")),price=price,rrp_price=amount(pick("rrp_price","rrp","sale_price")) if cur in ("BRL","R$") else None,currency="BRL" if cur in ("BRL","R$") else cur,group_key=group,merchant_category=category,category_name=text(pick("category_name"),180),brand=text(pick("brand_name","brand"),80),shop=shop,color=color,raw_colour=raw,audience=audience,sizes=[size] if size else [],in_stock=available,is_for_sale=on_sale,variant_count=1,source_updated_at=stamp,synced_at=datetime.now(timezone.utc).isoformat())
def combine(items):
    out={}
    for x in items:
        if x is None: continue
        prev=out.get(x["id"])
        if prev:
            # Lowest priced available variant, never an unavailable one when availability is known.
            choose=x if (x["in_stock"] and not prev["in_stock"]) or (x["in_stock"]==prev["in_stock"] and x["price"] is not None and (prev["price"] is None or x["price"]<prev["price"])) else prev
            sizes=sorted(set((prev["sizes"] if prev["in_stock"] else [])+(x["sizes"] if x["in_stock"] else [])))
            count=prev["variant_count"]+1
            out[x["id"]]={**choose,"sizes":sizes,"variant_count":count}
        else: out[x["id"]]=x
    return list(out.values())
def sync_catalog():
    publisher=os.environ["AWIN_PUBLISHER_ID"]
    key=os.environ["AWIN_FEED_KEY"]
    allowed={int(x) for x in os.environ.get("AWIN_MERCHANT_IDS","118977").split(",") if x.strip()}
    if not publisher.isdigit() or not key or not allowed: raise ValueError("Missing catalog config")
    url=f"https://ui.awin.com/productdata-darwin-download/publisher/{publisher}/{urllib.parse.quote(key,safe='')}/1/feedList"
    feeds=rows(get(url)); total=0; processed=set()
    for raw in feeds:
        r={norm(k):v for k,v in raw.items() if k}
        merchant=text(r.get("advertiser id"),20)
        if not merchant.isdigit() or int(merchant) not in allowed: continue
        if norm(r.get("membership status"))!="active" or norm(r.get("datafeed format"))!="awin": continue
        mid=int(merchant)
        if mid in processed: raise ValueError("Multiple feeds for merchant: configure one feed")
        feed=https(r.get("url"),{"productdata.awin.com","ui.awin.com"})
        if not feed: raise ValueError("Invalid feed URL")
        stamp=text(r.get("last imported"),40)
        try: stamp=datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc).isoformat()
        except ValueError: stamp=datetime.now(timezone.utc).isoformat()
        parsed=rows(get(feed))
        products=combine(normalize(x,mid,text(r.get("advertiser name"),80),stamp) for x in parsed)
        if not parsed or not products or not any(p["in_stock"] and p["is_for_sale"] for p in products): raise ValueError("Empty or unrecognized catalog; preserving existing rows")
        # Atomic per-merchant snapshot, with deletion guard server-side. No hard deletes.
        db("rpc/veste_catalog_snapshot_import",{"merchant":mid,"records":products,"expected_rows":len(parsed)})
        total+=len(products);processed.add(mid)
    if processed!=allowed: raise ValueError("One or more configured advertisers lack a supported active feed")
    log("catalog",True,total,"Approved Awin feeds imported; explicit stock flags applied")
def sync_transactions():
    pub=os.environ["AWIN_PUBLISHER_ID"]; token=os.environ["AWIN_API_TOKEN"]
    if not pub.isdigit() or not token: raise ValueError("Missing transaction config")
    now=datetime.now(timezone.utc); start=now-timedelta(days=30)
    params={"startDate":start.strftime("%Y-%m-%dT%H:%M:%S"),"endDate":now.strftime("%Y-%m-%dT%H:%M:%S"),"timezone":"UTC","dateType":"transaction","accessToken":token}
    data=json.loads(get(f"https://api.awin.com/publishers/{pub}/transactions/?"+urllib.parse.urlencode(params)))
    if not isinstance(data,list): raise ValueError("Unexpected transaction response")
    records=[]
    for x in data:
        sale=x.get("saleAmount") or {}; commission=x.get("commissionAmount") or {}
        if not isinstance(sale,dict) or not isinstance(commission,dict): raise ValueError("Unexpected monetary format")
        cur=text(commission.get("currency"),3)
        if not cur or cur!=text(sale.get("currency"),3): raise ValueError("Currency mismatch")
        sv=amount(sale.get("amount"),signed=True); cv=amount(commission.get("amount"),signed=True)
        if sv is None or cv is None or not x.get("id") or not x.get("transactionDate"): raise ValueError("Invalid transaction")
        records.append(dict(id=str(x["id"]),merchant_id=x.get("advertiserId"),transaction_at=x["transactionDate"],status=text(x.get("commissionStatus"),30),currency=cur,sale_amount=sv,commission_amount=cv))
    for i in range(0,len(records),200): db("rpc/veste_commerce_transactions_import",{"records":records[i:i+200]})
    log("transactions",True,len(records),"30-day Awin publisher report; grouped by status/currency")
def main():
    failed=False
    for kind,fn in [("catalog",sync_catalog),("transactions",sync_transactions)]:
        try: fn(); print(kind+": OK")
        except Exception as exc:
            failed=True; detail=type(exc).__name__+": sync not completed"
            print(kind+": "+detail,file=sys.stderr)
            try: log(kind,False,0,detail)
            except Exception: pass
    return int(failed)
if __name__=="__main__": raise SystemExit(main())
