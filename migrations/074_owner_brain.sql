-- 074: Owner Brain — the phone agent sells like the owner.
--
-- 1) owner_selling_notes: the owner's upsell instincts in their own words,
--    injected into the call prompt as a style/judgment block ("push the lamb
--    special on Fridays", "never push dessert at lunch"). NULL/empty = prompt
--    unchanged, same no-regression contract as restaurant_brief.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS owner_selling_notes TEXT;

-- 2) Caller-memory lookup path: the Vapi assistant-request now reads a
--    caller's order history (regulars → "welcome back, the usual?"). Index the
--    exact query shape so the hot path stays O(log n) as phone_orders grows.
CREATE INDEX IF NOT EXISTS idx_phone_orders_caller_history
    ON phone_orders (merchant_id, caller_phone, created_at DESC);
