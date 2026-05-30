-- Heatmap of transaction activity by (day_of_week, hour) for a merchant.
-- 0=Monday..6=Sunday to match the schedule UI's convention.
-- intensity is normalized 0..1 within the result.
create or replace function public.schedule_peak_hours(
  p_merchant_id uuid,
  p_weeks_back  integer default 8
)
returns table (
  day_of_week    smallint,
  hour           smallint,
  txn_count      bigint,
  revenue_cents  bigint,
  intensity      numeric
)
language sql
security definer
set search_path = public
as $$
  with bounded as (
    select transaction_at, total_cents
    from transactions
    where org_id = p_merchant_id
      and transaction_at >= now() - (p_weeks_back || ' weeks')::interval
      and total_cents is not null
  ),
  bucketed as (
    select
      -- Postgres extract(dow) is 0=Sunday..6=Saturday; remap to 0=Mon..6=Sun
      ((extract(dow from transaction_at)::int + 6) % 7)::smallint as day_of_week,
      extract(hour from transaction_at)::smallint                  as hour,
      count(*)::bigint                                             as txn_count,
      sum(total_cents)::bigint                                     as revenue_cents
    from bounded
    group by 1, 2
  ),
  scaled as (
    select
      day_of_week,
      hour,
      txn_count,
      revenue_cents,
      -- weight 70% on revenue, 30% on transaction count
      (0.7 * revenue_cents + 0.3 * txn_count) as raw_score
    from bucketed
  ),
  maxed as (
    select max(raw_score) as m from scaled
  )
  select
    s.day_of_week,
    s.hour,
    s.txn_count,
    s.revenue_cents,
    case when m.m > 0 then round((s.raw_score / m.m)::numeric, 4) else 0 end as intensity
  from scaled s
  cross join maxed m
  order by s.day_of_week, s.hour;
$$;

grant execute on function public.schedule_peak_hours(uuid, integer)
  to authenticated, service_role, anon;
