
create table veste_private.support_tickets (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 kind text not null check(kind in ('bug','suggestion','experience','privacy','delete_account')),
 message text not null check(char_length(message) between 1 and 2000),
 page text check(page in ('home','closet','looks','week','discover','style')),
 release text check(char_length(release)<=20),
 rating smallint check(rating between 1 and 5),
 status text not null default 'new' check(status in ('new','review','resolved','cancelled')),
 reply text not null default '' check(char_length(reply)<=2000),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index support_tickets_owner_idx on veste_private.support_tickets(user_id,created_at desc);
create unique index support_one_deletion on veste_private.support_tickets(user_id) where kind='delete_account' and status in ('new','review');
alter table veste_private.support_tickets enable row level security;
revoke all on veste_private.support_tickets from public, anon, authenticated;

create table veste_private.diagnostic_events(
 user_id uuid not null references auth.users(id) on delete cascade,
 code text not null check(code in ('boot','sync','diary_load','diary_save','catalog','weather')),
 minute timestamptz not null,
 primary key(user_id,code,minute)
);
alter table veste_private.diagnostic_events enable row level security;
revoke all on veste_private.diagnostic_events from public,anon,authenticated;
create index diagnostic_events_time_idx on veste_private.diagnostic_events(minute);
create or replace function veste_private.require_support_admin() returns void language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null or not exists(select 1 from veste_private.commerce_admins where user_id=auth.uid()) then raise exception 'Access denied' using errcode='42501'; end if;
end;$$;
create function veste_private.submit_support(p_kind text,p_message text,p_page text,p_release text,p_rating smallint) returns uuid language plpgsql security definer set search_path='' as $$
declare uid uuid:=auth.uid(); ticket uuid; k text:=p_kind; m text:=btrim(coalesce(p_message,''));
begin
 if uid is null or not exists(select 1 from auth.users where id=uid) then raise exception 'Authentication required' using errcode='42501';end if;
 perform pg_advisory_xact_lock(hashtextextended(uid::text,4519));
 if k='delete_account' then
  select id into ticket from veste_private.support_tickets where user_id=uid and kind=k and status in ('new','review') limit 1;
  if ticket is not null then return ticket;end if;
  m:='Solicitação de exclusão da conta e dos dados.';
 end if;
 if k is null or k not in ('bug','suggestion','experience','privacy','delete_account') or length(m)<1 or length(m)>2000 then raise exception 'Invalid request' using errcode='22023';end if;
 if (select count(*) from veste_private.support_tickets where user_id=uid and created_at>now()-interval '24 hours')>=10 and k not in ('privacy','delete_account') then raise exception 'Daily limit reached' using errcode='22023';end if;
 if (select count(*) from veste_private.support_tickets where user_id=uid and created_at>now()-interval '24 hours')>=30 then raise exception 'Daily limit reached' using errcode='22023';end if;
 insert into veste_private.support_tickets(user_id,kind,message,page,release,rating) values(uid,k,m,case when p_page in ('home','closet','looks','week','discover','style') then p_page end,left(p_release,20),p_rating) returning id into ticket;
 return ticket;
end;$$;
create function veste_private.my_support() returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Authentication required' using errcode='42501';end if;
 return coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at desc) from (select id,kind,message,status,reply,created_at,updated_at,rating from veste_private.support_tickets where user_id=auth.uid() order by created_at desc limit 100) x),'[]'::jsonb);
end;$$;
create function veste_private.cancel_deletion(p_id uuid) returns boolean language plpgsql security definer set search_path='' as $$
begin
 update veste_private.support_tickets set status='cancelled',updated_at=now() where id=p_id and user_id=auth.uid() and kind='delete_account' and status='new';
 return found;
end;$$;
create function veste_private.admin_support_snapshot() returns jsonb language plpgsql security definer set search_path='' as $$
declare tickets jsonb; diagnostics jsonb; resources jsonb; adoption jsonb;
begin
 perform veste_private.require_support_admin();
 select coalesce(jsonb_agg(to_jsonb(t) order by t.created_at desc),'[]'::jsonb) into tickets from (select s.id,s.kind,s.message,s.page,s.release,s.rating,s.status,s.reply,s.created_at,s.updated_at,u.email,case when s.kind='delete_account' then s.user_id end as deletion_user_id from veste_private.support_tickets s join auth.users u on u.id=s.user_id order by (s.status in ('new','review')) desc,s.created_at desc limit 250) t;
 select coalesce(jsonb_agg(to_jsonb(d)),'[]'::jsonb) into diagnostics from (select code,count(*) as events from veste_private.diagnostic_events where minute>=now()-interval '30 days' group by code order by count(*) desc) d;
 select jsonb_build_object('objects',count(*),'bytes',coalesce(sum(case when metadata->>'size' ~ '^[0-9]{1,16}$' then (metadata->>'size')::numeric else 0 end),0),'diary_photos',count(*) filter(where bucket_id='veste-photos' and name like '%/diary/%'),'db_bytes',pg_database_size(current_database())) into resources from storage.objects where bucket_id in ('veste-photos','veste-try-private');
 select jsonb_build_object('accounts',(select count(*) from auth.users),'synced',count(*),
 'profile_complete',count(*) filter(where c.settings#>>'{personalProfile,complete}'='true'),
 'closet_10',count(*) filter(where (select count(*) from jsonb_array_elements(c.pieces) p where not (p ? 'deletedAt') and coalesce(p->>'demo','false')<>'true' and coalesce(p->>'id','') not like 'veste-demo-%')>=10),
 'worn',count(*) filter(where exists(select 1 from jsonb_array_elements(case when jsonb_typeof(c.settings->'wearHistory')='array' then c.settings->'wearHistory' else '[]'::jsonb end) w where coalesce(w->>'demo','false')<>'true' and coalesce(w->>'key','') not like '%veste-demo-%')),
 'diary_users',(select count(distinct user_id) from public.veste_style_diary where photo_path is not null)) into adoption from public.veste_closets c;
 return jsonb_build_object('tickets',tickets,'open_count',(select count(*) from veste_private.support_tickets where status in ('new','review')),'diagnostics',diagnostics,'resources',resources,'adoption',adoption);
end;$$;
create function veste_private.admin_support_update(p_id uuid,p_status text,p_reply text) returns boolean language plpgsql security definer set search_path='' as $$
begin
 perform veste_private.require_support_admin();
 if p_status not in ('new','review','resolved','cancelled') or length(coalesce(p_reply,''))>2000 then raise exception 'Invalid status or reply' using errcode='22023';end if;
 update veste_private.support_tickets set status=p_status,reply=btrim(coalesce(p_reply,'')),updated_at=now() where id=p_id and not(kind='delete_account' and p_status='resolved');
 return found;
end;$$;
create function veste_private.record_diagnostic(p_code text) returns boolean language plpgsql security definer set search_path='' as $$
declare uid uuid:=auth.uid();
begin
 if uid is null or p_code not in ('boot','sync','diary_load','diary_save','catalog','weather') or not exists(select 1 from auth.users where id=uid) then return false;end if;
 if (select count(*) from veste_private.diagnostic_events where user_id=uid and minute>now()-interval '24 hours')>=60 then return false;end if;
 insert into veste_private.diagnostic_events values(uid,p_code,date_trunc('minute',now())) on conflict do nothing;
 return found;
end;$$;
create function public.veste_submit_support(p_kind text,p_message text,p_page text,p_release text,p_rating smallint default null) returns uuid language sql set search_path='' as $$select veste_private.submit_support(p_kind,p_message,p_page,p_release,p_rating)$$;
create function public.veste_my_support() returns jsonb language sql set search_path='' as $$select veste_private.my_support()$$;
create function public.veste_cancel_deletion(p_id uuid) returns boolean language sql set search_path='' as $$select veste_private.cancel_deletion(p_id)$$;
create function public.veste_admin_support_snapshot() returns jsonb language sql set search_path='' as $$select veste_private.admin_support_snapshot()$$;
create function public.veste_admin_support_update(p_id uuid,p_status text,p_reply text) returns boolean language sql set search_path='' as $$select veste_private.admin_support_update(p_id,p_status,p_reply)$$;
create function public.veste_record_diagnostic(p_code text) returns boolean language sql set search_path='' as $$select veste_private.record_diagnostic(p_code)$$;
revoke all on function veste_private.require_support_admin() from public,anon,authenticated;
revoke all on function veste_private.submit_support(text,text,text,text,smallint), public.veste_submit_support(text,text,text,text,smallint) from public,anon,authenticated;
grant execute on function veste_private.submit_support(text,text,text,text,smallint), public.veste_submit_support(text,text,text,text,smallint) to authenticated;
revoke all on function veste_private.my_support(), public.veste_my_support() from public,anon,authenticated;
grant execute on function veste_private.my_support(), public.veste_my_support() to authenticated;
revoke all on function veste_private.cancel_deletion(uuid), public.veste_cancel_deletion(uuid) from public,anon,authenticated;
grant execute on function veste_private.cancel_deletion(uuid), public.veste_cancel_deletion(uuid) to authenticated;
revoke all on function veste_private.admin_support_snapshot(), public.veste_admin_support_snapshot() from public,anon,authenticated;
grant execute on function veste_private.admin_support_snapshot(), public.veste_admin_support_snapshot() to authenticated;
revoke all on function veste_private.admin_support_update(uuid,text,text), public.veste_admin_support_update(uuid,text,text) from public,anon,authenticated;
grant execute on function veste_private.admin_support_update(uuid,text,text), public.veste_admin_support_update(uuid,text,text) to authenticated;
revoke all on function veste_private.record_diagnostic(text), public.veste_record_diagnostic(text) from public,anon,authenticated;
grant execute on function veste_private.record_diagnostic(text), public.veste_record_diagnostic(text) to authenticated;
grant usage on schema veste_private to authenticated;
select cron.schedule('veste-diagnostic-retention','50 4 * * *',$$delete from veste_private.diagnostic_events where minute<now()-interval '30 days';$$);
