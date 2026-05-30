-- Projected weekly revenue: trailing average across the last N weeks of POS data.
-- Used to compute labor % (scheduled labor cost / projected revenue).
create or replace function public.schedule_projected_weekly_revenue(
  p_merchant_id uuid,
  p_weeks_back  integer default 8
)
returns bigint
language sql
security definer
set search_path = public
as $$
  select (coalesce(sum(total_cents), 0) / greatest(p_weeks_back, 1))::bigint
  from transactions
  where org_id = p_merchant_id
    and transaction_at >= now() - (p_weeks_back || ' weeks')::interval
    and total_cents is not null;
$$;

grant execute on function public.schedule_projected_weekly_revenue(uuid, integer)
  to authenticated, service_role, anon;
