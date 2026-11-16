-- Read-only, paginated directory for authorized VESTE administrators.
create or replace function veste_private.admin_account_directory(p_limit integer default 50, p_offset integer default 0, p_search text default '', p_status text default 'all')
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb; lim integer:=least(100,greatest(1,coalesce(p_limit,50))); off integer:=greatest(0,coalesce(p_offset,0)); term text:=lower(left(btrim(coalesce(p_search,'')),200));
begin
 perform veste_private.require_support_admin();
 if p_status is null or p_status not in ('all','confirmed','pending') then raise exception 'Invalid filter' using errcode='22023';end if;
 with accounts as (
  select u.id,u.email,u.created_at,u.last_sign_in_at,u.email_confirmed_at is not null as confirmed,
  case when u.raw_app_meta_data->>'provider'='google' then 'google' when u.raw_app_meta_data->>'provider'='email' then 'email' else 'other' end as provider,
  exists(select 1 from veste_private.commerce_admins a where a.user_id=u.id) as administrator
  from auth.users u
 ), filtered as (
  select * from accounts a where (term='' or strpos(lower(coalesce(a.email,'')),term)>0)
  and (p_status='all' or (p_status='confirmed' and a.confirmed) or (p_status='pending' and not a.confirmed))
 ), page as (
  select email,created_at,last_sign_in_at,confirmed,provider,administrator,id=auth.uid() as current_account from filtered
  order by created_at desc nulls last,id limit lim offset off
 )
 select jsonb_build_object('total',(select count(*) from accounts),'confirmed',(select count(*) from accounts where confirmed),'signed_in',(select count(*) from accounts where last_sign_in_at is not null),'filtered',(select count(*) from filtered),'limit',lim,'offset',off,'rows',coalesce((select jsonb_agg(to_jsonb(page) order by created_at desc nulls last) from page),'[]'::jsonb)) into result;
 return result;
end;$$;
create or replace function public.veste_admin_account_directory(p_limit integer default 50,p_offset integer default 0,p_search text default '',p_status text default 'all')
returns jsonb language sql stable security invoker set search_path='' as $$select veste_private.admin_account_directory(p_limit,p_offset,p_search,p_status)$$;
revoke all on function veste_private.admin_account_directory(integer,integer,text,text), public.veste_admin_account_directory(integer,integer,text,text) from public,anon,authenticated;
grant execute on function veste_private.admin_account_directory(integer,integer,text,text), public.veste_admin_account_directory(integer,integer,text,text) to authenticated;
