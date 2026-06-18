-- POS atomic write RPC — OPTIONAL Step C (propagate) hardening
-- =====================================================================
-- Wraps the three SyncResult writes (products, transactions, transaction_items)
-- in ONE transaction so a partial failure can't leave a transaction without its
-- line items. A plpgsql function body is a single transaction: any error rolls
-- back all three upserts.
--
-- The app calls this ONLY when POS_ATOMIC_WRITE=1 (see _write_sync_result in
-- src/api/routes/pos_connections.py). The default path is sequential idempotent
-- upserts, which is already self-healing on retry thanks to deterministic ids —
-- so this RPC is an enhancement, not a prerequisite.
--
-- ⚠️ VALIDATE BEFORE ENABLING THE FLAG:
--   • The ON CONFLICT DO UPDATE column lists below are the mapper-written fields;
--     confirm them against the live schema. jsonb_populate_recordset maps by
--     name and IGNORES keys with no matching column (so the transient `provider`
--     hint + extra metadata keys are harmless), but a column OMITTED from the
--     JSON is populated as NULL — keep DO UPDATE to columns the mappers set, or a
--     re-sync could overwrite good data with NULL.
--   • This writes the BASE tables only; it does NOT do per-provider routing. Do
--     NOT enable POS_ATOMIC_WRITE together with POS_PER_PROVIDER_TABLES until the
--     function is extended to route rows to {provider}_{table}.
-- =====================================================================

create or replace function public.pos_sync_upsert(
    _products jsonb default '[]'::jsonb,
    _transactions jsonb default '[]'::jsonb,
    _transaction_items jsonb default '[]'::jsonb
) returns jsonb
language plpgsql
security definer
as $$
declare
    p_count int := 0;
    t_count int := 0;
    i_count int := 0;
begin
    if jsonb_array_length(_products) > 0 then
        insert into public.products
        select * from jsonb_populate_recordset(null::public.products, _products)
        on conflict (org_id, external_id) do update set
            name        = excluded.name,
            price_cents = excluded.price_cents,
            cost_cents  = excluded.cost_cents,
            updated_at  = excluded.updated_at;
        get diagnostics p_count = row_count;
    end if;

    if jsonb_array_length(_transactions) > 0 then
        insert into public.transactions
        select * from jsonb_populate_recordset(null::public.transactions, _transactions)
        on conflict (org_id, external_id) do update set
            total_cents    = excluded.total_cents,
            tax_cents      = excluded.tax_cents,
            tip_cents      = excluded.tip_cents,
            discount_cents = excluded.discount_cents,
            payment_method = excluded.payment_method,
            type           = excluded.type,
            metadata       = excluded.metadata;
        get diagnostics t_count = row_count;
    end if;

    if jsonb_array_length(_transaction_items) > 0 then
        insert into public.transaction_items
        select * from jsonb_populate_recordset(null::public.transaction_items, _transaction_items)
        on conflict (id, transaction_at) do update set
            quantity         = excluded.quantity,
            unit_price_cents = excluded.unit_price_cents,
            total_cents      = excluded.total_cents,
            discount_cents   = excluded.discount_cents,
            product_id       = excluded.product_id;
        get diagnostics i_count = row_count;
    end if;

    return jsonb_build_object(
        'products', p_count, 'transactions', t_count, 'transaction_items', i_count
    );
end;
$$;
