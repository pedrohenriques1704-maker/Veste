CREATE OR REPLACE FUNCTION public.veste_catalog_snapshot_import(merchant bigint, records jsonb, expected_rows integer)
 RETURNS integer
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare n integer; previous_n integer; matching_n integer; variants integer;
begin
 if merchant is null or expected_rows<1 or jsonb_typeof(records)<>'array' or jsonb_array_length(records)<1 or jsonb_array_length(records)>15000 then raise exception 'Invalid catalog batch';end if;
 create temporary table veste_import_rows on commit drop as select * from jsonb_populate_recordset(null::public.veste_catalog_products,records);
 create unique index on pg_temp.veste_import_rows(id);
 analyze pg_temp.veste_import_rows;
 if exists(select 1 from pg_temp.veste_import_rows r where r.merchant_id is distinct from merchant or r.source is distinct from 'awin' or r.id is distinct from ('awin:'||merchant::text||':'||r.merchant_product_id) or r.source_updated_at is null or r.synced_at is null or r.variant_count is null) then raise exception 'Invalid catalog row';end if;
 select count(*),coalesce(sum(r.variant_count),0) into n,variants from pg_temp.veste_import_rows r;
 if variants>expected_rows or variants<expected_rows*.7 then raise exception 'Incomplete or unsupported feed';end if;
 perform pg_advisory_xact_lock(merchant);
 select count(*) into previous_n from public.veste_catalog_products where merchant_id=merchant and source='awin' and in_stock and is_for_sale;
 select count(*) into matching_n from public.veste_catalog_products p join pg_temp.veste_import_rows r on r.id=p.id where p.merchant_id=merchant and p.source='awin' and p.in_stock and p.is_for_sale;
 if previous_n>0 and matching_n<previous_n*.6 then raise exception 'Catalog identity/coverage mismatch';end if;
 if exists(select 1 from public.veste_catalog_products p join pg_temp.veste_import_rows r on r.id=p.id where p.source_updated_at>r.source_updated_at) then raise exception 'Feed older than existing catalog';end if;
 insert into public.veste_catalog_products(id,source,merchant_id,merchant_product_id,awin_product_id,name,description,affiliate_url,merchant_url,image_url,price,rrp_price,currency,group_key,merchant_category,category_name,brand,shop,color,raw_colour,audience,sizes,in_stock,is_for_sale,source_updated_at,variant_count,synced_at)
 select r.id,r.source,r.merchant_id,r.merchant_product_id,r.awin_product_id,r.name,r.description,r.affiliate_url,r.merchant_url,r.image_url,r.price,r.rrp_price,r.currency,r.group_key,r.merchant_category,r.category_name,r.brand,r.shop,r.color,r.raw_colour,r.audience,r.sizes,r.in_stock,r.is_for_sale,r.source_updated_at,r.variant_count,r.synced_at from pg_temp.veste_import_rows r
 on conflict(id) do update set source=excluded.source,merchant_id=excluded.merchant_id,merchant_product_id=excluded.merchant_product_id,awin_product_id=excluded.awin_product_id,name=excluded.name,description=excluded.description,affiliate_url=excluded.affiliate_url,merchant_url=excluded.merchant_url,image_url=excluded.image_url,price=excluded.price,rrp_price=excluded.rrp_price,currency=excluded.currency,group_key=excluded.group_key,merchant_category=excluded.merchant_category,category_name=excluded.category_name,brand=excluded.brand,shop=excluded.shop,color=excluded.color,raw_colour=excluded.raw_colour,audience=excluded.audience,sizes=excluded.sizes,in_stock=excluded.in_stock,is_for_sale=excluded.is_for_sale,source_updated_at=excluded.source_updated_at,variant_count=excluded.variant_count,synced_at=excluded.synced_at;
 if variants>=expected_rows*.95 and matching_n>=previous_n*.8 then
  update public.veste_catalog_products p set in_stock=false,is_for_sale=false,synced_at=now() where p.merchant_id=merchant and p.source='awin' and not exists(select 1 from pg_temp.veste_import_rows r where r.id=p.id);
 end if;
 return n;
end;$function$;
