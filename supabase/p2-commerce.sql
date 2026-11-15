-- P2 commerce. Apply to the project before publishing the frontend.
create schema if not exists veste_private;
revoke all on schema veste_private from public;
grant usage on schema veste_private to authenticated;
create table if not exists veste_private.commerce_admins(user_id uuid primary key references auth.users(id) on delete cascade);
alter table veste_private.commerce_admins enable row level security;
create table if not exists veste_private.product_clicks(day date not null,product_id text not null,actor_bucket text not null,primary key(day,product_id,actor_bucket));
alter table veste_private.product_clicks enable row level security;
create table if not exists veste_private.commerce_sync_runs(id bigint generated always as identity primary key,kind text not null,finished_at timestamptz not null default now(),ok boolean not null,records integer not null default 0,detail text not null default '');
alter table veste_private.commerce_sync_runs enable row level security;
create table if not exists veste_private.commerce_transactions(id text primary key,merchant_id bigint,transaction_at timestamptz not null,status text not null,currency text not null,sale_amount numeric not null,commission_amount numeric not null,attributed boolean not null default false,transaction_type text not null default '');
alter table veste_private.commerce_transactions add column if not exists attributed boolean not null default false;
alter table veste_private.commerce_transactions add column if not exists transaction_type text not null default '';
alter table veste_private.commerce_transactions enable row level security;
create or replace function veste_private.record_product_click(product_key text) returns boolean language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null or product_key is null or length(product_key)>240 then return false; end if;
 if not exists(select 1 from public.veste_catalog_products p where p.id=product_key and p.in_stock and p.is_for_sale) then return false; end if;
 insert into veste_private.product_clicks(day,product_id,actor_bucket) values ((now() at time zone 'UTC')::date,product_key,md5(auth.uid()::text||':'||date_trunc('minute',now())::text)) on conflict do nothing;
 return true;
end;$$;
revoke all on function veste_private.record_product_click(text) from public,anon,authenticated;
grant execute on function veste_private.record_product_click(text) to authenticated;
create or replace function public.veste_record_product_click(product_key text) returns boolean language sql security invoker set search_path='' as $$ select veste_private.record_product_click(product_key) $$;
revoke all on function public.veste_record_product_click(text) from public,anon,authenticated;
grant execute on function public.veste_record_product_click(text) to authenticated;
create or replace function veste_private.admin_snapshot() returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 if auth.uid() is null or not exists(select 1 from veste_private.commerce_admins a where a.user_id=auth.uid()) then raise exception 'Access denied' using errcode='42501'; end if;
 select jsonb_build_object('accounts',(select count(*) from auth.users),'catalog',(select count(*) from public.veste_catalog_products),'available',(select count(*) from public.veste_catalog_products where in_stock and is_for_sale),'shops',(select count(distinct merchant_id) from public.veste_catalog_products where in_stock and is_for_sale),'last_catalog',(select max(synced_at) from public.veste_catalog_products),'clicks30',(select count(*) from veste_private.product_clicks where day>=current_date-29),'daily_clicks',(select coalesce(jsonb_agg(to_jsonb(t) order by t.day),'[]'::jsonb) from (select day,count(*) as clicks from veste_private.product_clicks where day>=current_date-29 group by day)t),'partners',(select coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) from (select merchant_id,max(shop) as shop,count(*) as products,count(*) filter(where in_stock and is_for_sale) as available,max(synced_at) as synced_at from public.veste_catalog_products group by merchant_id order by max(shop))t),'sync',(select coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) from (select kind,finished_at,ok,records,detail from veste_private.commerce_sync_runs order by finished_at desc limit 15)t),'financial',(select coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) from (select coalesce((select max(p.shop) from public.veste_catalog_products p where p.merchant_id=c.merchant_id),c.merchant_id::text,'Não identificado') as shop,c.currency,c.status,count(*) as transactions,count(*) filter(where lower(c.transaction_type) in ('sale','mobile sale')) as conversions,sum(c.sale_amount) as sales,sum(c.commission_amount) as commissions from veste_private.commerce_transactions c where c.transaction_at>=now()-interval '30 days' and c.attributed group by c.merchant_id,c.currency,c.status)t),'report_ready',exists(select 1 from veste_private.commerce_sync_runs where kind='transactions' and ok)) into result;
 return result;
end;$$;
revoke all on function veste_private.admin_snapshot() from public,anon,authenticated;
grant execute on function veste_private.admin_snapshot() to authenticated;
create or replace function public.veste_admin_snapshot() returns jsonb language sql security invoker set search_path='' as $$select veste_private.admin_snapshot()$$;
revoke all on function public.veste_admin_snapshot() from public,anon,authenticated;
grant execute on function public.veste_admin_snapshot() to authenticated;
create or replace function public.veste_commerce_sync_log(sync_kind text,success boolean,record_count integer,summary text) returns void language sql security invoker set search_path='' as $$insert into veste_private.commerce_sync_runs(kind,ok,records,detail) values(sync_kind,success,greatest(record_count,0),left(summary,180))$$;
revoke all on function public.veste_commerce_sync_log(text,boolean,integer,text) from public,anon,authenticated;
grant usage on schema veste_private to service_role;
grant insert on veste_private.commerce_sync_runs to service_role;
grant usage on sequence veste_private.commerce_sync_runs_id_seq to service_role;
grant execute on function public.veste_commerce_sync_log(text,boolean,integer,text) to service_role;
create or replace function public.veste_commerce_transactions_import(records jsonb) returns integer language plpgsql security invoker set search_path='' as $$declare n int; begin
 insert into veste_private.commerce_transactions(id,merchant_id,transaction_at,status,currency,sale_amount,commission_amount,attributed,transaction_type)
 select id,merchant_id,transaction_at,status,currency,sale_amount,commission_amount,coalesce(attributed,false),coalesce(transaction_type,'') from jsonb_to_recordset(records) as x(id text,merchant_id bigint,transaction_at timestamptz,status text,currency text,sale_amount numeric,commission_amount numeric,attributed boolean,transaction_type text)
 on conflict(id) do update set merchant_id=excluded.merchant_id,transaction_at=excluded.transaction_at,status=excluded.status,currency=excluded.currency,sale_amount=excluded.sale_amount,commission_amount=excluded.commission_amount,attributed=excluded.attributed,transaction_type=excluded.transaction_type;
 get diagnostics n=row_count;return n;end;$$;
revoke all on function public.veste_commerce_transactions_import(jsonb) from public,anon,authenticated;
grant select,insert,update on veste_private.commerce_transactions to service_role;
grant execute on function public.veste_commerce_transactions_import(jsonb) to service_role;
-- Administrator provisioning is a separate privileged deployment step, never a public client operation.

-- Atomic catalog import, never hard-delete. Unknown/partial feeds cannot retire old offers.
create or replace function public.veste_catalog_snapshot_import(merchant bigint,records jsonb,expected_rows integer)
returns integer language plpgsql security invoker set search_path='' as $$
declare n integer; previous_n integer; matching_n integer; variants integer;
begin
 if merchant is null or expected_rows<1 or jsonb_typeof(records)<>'array' or jsonb_array_length(records)<1 or jsonb_array_length(records)>15000 then raise exception 'Invalid catalog batch';end if;
 if exists(select 1 from jsonb_populate_recordset(null::public.veste_catalog_products,records) r where r.merchant_id is distinct from merchant or r.source is distinct from 'awin' or r.id is distinct from ('awin:'||merchant::text||':'||r.merchant_product_id) or r.source_updated_at is null or r.synced_at is null or r.variant_count is null) then raise exception 'Invalid catalog row';end if;
 select count(*),coalesce(sum(r.variant_count),0) into n,variants from jsonb_populate_recordset(null::public.veste_catalog_products,records) r;
 if variants>expected_rows or variants<expected_rows*.7 then raise exception 'Incomplete or unsupported feed';end if;
 perform pg_advisory_xact_lock(merchant);
 select count(*) into previous_n from public.veste_catalog_products where merchant_id=merchant and source='awin' and in_stock and is_for_sale;
 select count(*) into matching_n from public.veste_catalog_products p join jsonb_populate_recordset(null::public.veste_catalog_products,records) r on r.id=p.id where p.merchant_id=merchant and p.source='awin' and p.in_stock and p.is_for_sale;
 if previous_n>0 and matching_n<previous_n*.6 then raise exception 'Catalog identity/coverage mismatch';end if;
 if exists(select 1 from public.veste_catalog_products p join jsonb_populate_recordset(null::public.veste_catalog_products,records) r on r.id=p.id where p.source_updated_at>r.source_updated_at) then raise exception 'Feed older than existing catalog';end if;
 insert into public.veste_catalog_products(id,source,merchant_id,merchant_product_id,awin_product_id,name,description,affiliate_url,merchant_url,image_url,price,rrp_price,currency,group_key,merchant_category,category_name,brand,shop,color,raw_colour,audience,sizes,in_stock,is_for_sale,source_updated_at,variant_count,synced_at)
 select r.id,r.source,r.merchant_id,r.merchant_product_id,r.awin_product_id,r.name,r.description,r.affiliate_url,r.merchant_url,r.image_url,r.price,r.rrp_price,r.currency,r.group_key,r.merchant_category,r.category_name,r.brand,r.shop,r.color,r.raw_colour,r.audience,r.sizes,r.in_stock,r.is_for_sale,r.source_updated_at,r.variant_count,r.synced_at from jsonb_populate_recordset(null::public.veste_catalog_products,records) r
 on conflict(id) do update set source=excluded.source,merchant_id=excluded.merchant_id,merchant_product_id=excluded.merchant_product_id,awin_product_id=excluded.awin_product_id,name=excluded.name,description=excluded.description,affiliate_url=excluded.affiliate_url,merchant_url=excluded.merchant_url,image_url=excluded.image_url,price=excluded.price,rrp_price=excluded.rrp_price,currency=excluded.currency,group_key=excluded.group_key,merchant_category=excluded.merchant_category,category_name=excluded.category_name,brand=excluded.brand,shop=excluded.shop,color=excluded.color,raw_colour=excluded.raw_colour,audience=excluded.audience,sizes=excluded.sizes,in_stock=excluded.in_stock,is_for_sale=excluded.is_for_sale,source_updated_at=excluded.source_updated_at,variant_count=excluded.variant_count,synced_at=excluded.synced_at;
 if variants>=expected_rows*.95 and matching_n>=previous_n*.8 then
  update public.veste_catalog_products p set in_stock=false,is_for_sale=false,synced_at=now() where p.merchant_id=merchant and p.source='awin' and not exists(select 1 from jsonb_populate_recordset(null::public.veste_catalog_products,records) r where r.id=p.id);
 end if;
 return n;
end;$$;
revoke all on function public.veste_catalog_snapshot_import(bigint,jsonb,integer) from public,anon,authenticated;
grant execute on function public.veste_catalog_snapshot_import(bigint,jsonb,integer) to service_role;
