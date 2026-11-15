-- VESTE 7.3.1: consent-based, first-party aggregate product usage.
create table if not exists veste_private.analytics_config(
 singleton boolean primary key default true check(singleton), salt text not null, started_at timestamptz not null default now()
);
alter table veste_private.analytics_config enable row level security;
revoke all on veste_private.analytics_config from public,anon,authenticated;
insert into veste_private.analytics_config(singleton,salt) values(true,encode(extensions.gen_random_bytes(32),'hex')) on conflict(singleton) do nothing;
create table if not exists veste_private.page_views(
 event_id uuid primary key, account_key text not null, session_key text not null,
 page text not null check(page in ('home','closet','looks','week','discover','style')),
 viewed_at timestamptz not null default now()
);
alter table veste_private.page_views enable row level security;
revoke all on veste_private.page_views from public,anon,authenticated;
create index if not exists veste_page_views_time_idx on veste_private.page_views(viewed_at);
create index if not exists veste_page_views_account_time_idx on veste_private.page_views(account_key,viewed_at);
create or replace function veste_private.record_page_view(page_key text,session_id uuid,view_id uuid) returns boolean
language plpgsql security definer set search_path='' as $$
declare actor text; sess text; secret text;
begin
 if auth.uid() is null or page_key is null or page_key not in ('home','closet','looks','week','discover','style') or session_id is null or view_id is null then return false;end if;
 select salt into secret from veste_private.analytics_config where singleton;
 if secret is null then return false;end if;
 actor=encode(extensions.hmac(auth.uid()::text,secret,'sha256'),'hex');
 sess=encode(extensions.hmac(auth.uid()::text||':'||session_id::text,secret,'sha256'),'hex');
 perform pg_advisory_xact_lock(hashtextextended(actor,0));
 if (select count(*) from veste_private.page_views where account_key=actor and viewed_at>=now()-interval '1 minute')>=60 then return false;end if;
 insert into veste_private.page_views(event_id,account_key,session_key,page) values(view_id,actor,sess,page_key) on conflict(event_id) do nothing;
 return true;
end;$$;
revoke all on function veste_private.record_page_view(text,uuid,uuid) from public,anon,authenticated;
grant execute on function veste_private.record_page_view(text,uuid,uuid) to authenticated;
create or replace function public.veste_record_page_view(page_key text,session_id uuid,view_id uuid) returns boolean language sql security invoker set search_path='' as $$select veste_private.record_page_view(page_key,session_id,view_id)$$;
revoke all on function public.veste_record_page_view(text,uuid,uuid) from public,anon,authenticated;
grant execute on function public.veste_record_page_view(text,uuid,uuid) to authenticated;
create or replace function veste_private.admin_usage_snapshot(period_days integer) returns jsonb
language plpgsql security definer set search_path='' as $$
declare today date:=(now() at time zone 'America/Sao_Paulo')::date; first_day date; started timestamptz; result jsonb; since timestamptz;
begin
 if auth.uid() is null or not exists(select 1 from veste_private.commerce_admins where user_id=auth.uid()) then raise exception 'Access denied' using errcode='42501';end if;
 if period_days is null or period_days not in (7,30,90) then raise exception 'Invalid period' using errcode='22023';end if;
 first_day=today-(period_days-1);since=first_day::timestamp at time zone 'America/Sao_Paulo';
 select started_at into started from veste_private.analytics_config where singleton;
 with events as materialized (select *, (viewed_at at time zone 'America/Sao_Paulo')::date as local_day from veste_private.page_views where viewed_at>=since),
 daily as (select local_day,count(*) as views,count(distinct account_key) as users,count(distinct session_key) as sessions from events group by local_day),
 page_counts as (select page,count(*) as views,count(distinct account_key) as users,count(distinct session_key) as sessions from events group by page),
 active_days as (select account_key,count(distinct local_day) as days from events group by account_key)
 select jsonb_build_object(
 'started_at',started,'period_days',period_days,'views',(select count(*) from events),'sessions',(select count(distinct session_key) from events),'users',(select count(distinct account_key) from events),
 'today_users',(select count(distinct account_key) from veste_private.page_views where viewed_at>=today::timestamp at time zone 'America/Sao_Paulo'),
 'users7',(select count(distinct account_key) from veste_private.page_views where viewed_at>=(today-6)::timestamp at time zone 'America/Sao_Paulo'),
 'users30',(select count(distinct account_key) from veste_private.page_views where viewed_at>=(today-29)::timestamp at time zone 'America/Sao_Paulo'),
 'new_accounts',(select count(*) from auth.users where created_at>=since),
 'returning_users',(select count(*) from active_days where days>=2),
 'daily',(select coalesce(jsonb_agg(jsonb_build_object('day',d.local_day,'views',coalesce(a.views,0),'users',coalesce(a.users,0),'sessions',coalesce(a.sessions,0)) order by d.local_day),'[]'::jsonb) from (select first_day+i as local_day from generate_series(0,period_days-1) i where first_day+i >= (started at time zone 'America/Sao_Paulo')::date)d left join daily a using(local_day)),
 'pages',(select coalesce(jsonb_agg(jsonb_build_object('page',p.page,'views',coalesce(c.views,0),'users',coalesce(c.users,0),'sessions',coalesce(c.sessions,0)) order by coalesce(c.views,0) desc,p.page),'[]'::jsonb) from unnest(array['home','closet','looks','week','discover','style']) p(page) left join page_counts c using(page))
 ) into result;
 return result;
end;$$;
revoke all on function veste_private.admin_usage_snapshot(integer) from public,anon,authenticated;
grant execute on function veste_private.admin_usage_snapshot(integer) to authenticated;
create or replace function public.veste_admin_usage_snapshot(period_days integer) returns jsonb language sql security invoker set search_path='' as $$select veste_private.admin_usage_snapshot(period_days)$$;
revoke all on function public.veste_admin_usage_snapshot(integer) from public,anon,authenticated;
grant execute on function public.veste_admin_usage_snapshot(integer) to authenticated;
-- Keep raw pseudonymous events for 90 days; hourly-independent daily cleanup.
select cron.schedule('veste-analytics-retention','45 4 * * *',$cron$delete from veste_private.page_views where viewed_at < now()-interval '90 days'$cron$);

-- Read-only administrative roster.
create or replace function veste_private.admin_access_roster() returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 if auth.uid() is null or not exists(select 1 from veste_private.commerce_admins a where a.user_id=auth.uid()) then raise exception 'Access denied' using errcode='42501';end if;
 select coalesce(jsonb_agg(jsonb_build_object('email',u.email,'created_at',u.created_at,'last_sign_in_at',u.last_sign_in_at,'current_account',u.id=auth.uid()) order by u.email),'[]'::jsonb) into result from veste_private.commerce_admins a join auth.users u on u.id=a.user_id;
 return result;
end;$$;
revoke all on function veste_private.admin_access_roster() from public,anon,authenticated;
grant execute on function veste_private.admin_access_roster() to authenticated;
create or replace function public.veste_admin_access_roster() returns jsonb language sql security invoker set search_path='' as $$select veste_private.admin_access_roster()$$;
revoke all on function public.veste_admin_access_roster() from public,anon,authenticated;
grant execute on function public.veste_admin_access_roster() to authenticated;
