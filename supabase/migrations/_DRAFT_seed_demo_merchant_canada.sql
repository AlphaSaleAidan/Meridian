-- DRAFT — do NOT apply until Session 1 (LLMClient refactor) is merged to
-- swarm-upgrade and deployed to api.meridian.tips. Per the gate locked
-- on 2026-06-04: if this row is applied while voice is still running
-- the pre-Session-1 hardcoded DEMO_MENU path, the row sits unread and
-- gives a false impression that per-merchant menus are live when they
-- aren't.
--
-- After Session 1 deploys:
--   1. Rename: mv _DRAFT_seed_demo_merchant_canada.sql 20260604_seed_demo_merchant_canada.sql
--   2. Apply via the supabase migration tool (or psql against prod).
--   3. Run scripts/provision_meridian_twilio_number.py with the purchased
--      Canadian DID and update phone_agent_config.phone_number from
--      NULL to that DID. (The provisioning script can do this for you.)
--
-- Square OAuth is the normal flow (live production credentials, not
-- sandbox — sandbox-CAD detour dropped 2026-06-04). Demo merchant will
-- complete Square OAuth via the merchant onboarding wizard like any
-- other merchant; until then pos_access_token stays NULL and
-- create_pos_order falls through to logs-only (order persists in
-- Supabase, no Square call attempted). That fallback is what makes the
-- demo non-breaking before OAuth completes.

INSERT INTO phone_agent_config (
    merchant_id,
    business_name,
    business_type,
    phone_number,
    greeting,
    voice,
    language,
    active,
    menu_items,
    pos_system,
    pos_access_token,
    pos_location_id,
    business_hours,
    after_hours_message,
    max_concurrent_calls,
    order_types,
    special_instructions_enabled,
    transfer_number,
    sms_checkout_enabled,
    sms_ordering_enabled,
    tax_rate,
    demo_safe
) VALUES (
    'demo-merchant',
    'Meridian Demo Restaurant',
    'restaurant',
    NULL,  -- populated post-DID-purchase by provision_meridian_twilio_number.py
    'Thanks for calling Meridian Demo Restaurant! What can I get for you today?',
    'af_bella',  -- Pipecat voice; ignored on the Twilio Gather path which uses Polly.Joanna
    'en',        -- en-US Polly; no en-CA Polly voice exists, acceptable for v1
    true,
    -- Demo menu kept small and Canadian-typical. CAD pricing.
    '[
        {"name": "Maple Bacon Burger", "price": 14.99, "sizes": ["regular", "double"], "category": "Burgers"},
        {"name": "Chicken Tenders", "price": 11.49, "sizes": ["3-piece", "5-piece"], "category": "Mains"},
        {"name": "Poutine", "price": 8.99, "sizes": ["small", "large"], "modifications": ["gravy on side", "no cheese curds"], "category": "Sides"},
        {"name": "Caesar Salad", "price": 9.99, "sizes": ["side", "full"], "category": "Salads"},
        {"name": "Fries", "price": 4.99, "sizes": ["small", "medium", "large"], "category": "Sides"},
        {"name": "Onion Rings", "price": 5.99, "category": "Sides"},
        {"name": "Coca-Cola", "price": 2.99, "sizes": ["small", "medium", "large"], "category": "Drinks"},
        {"name": "Iced Tea", "price": 3.49, "sizes": ["small", "medium", "large"], "category": "Drinks"},
        {"name": "Milkshake", "price": 6.99, "modifications": ["chocolate", "vanilla", "strawberry"], "category": "Drinks"},
        {"name": "Butter Tart", "price": 4.49, "category": "Desserts"}
    ]'::jsonb,
    'square',  -- sandbox; pos_access_token NULL until Square-sandbox-CAD check passes
    NULL,
    NULL,
    -- Business hours: open every day 10:00-22:00 America/Toronto (stored
    -- as UTC strings; is_within_business_hours compares naive HH:MM).
    -- Adjust per merchant once a real one onboards.
    '{
        "monday":    {"open": "14:00", "close": "02:00"},
        "tuesday":   {"open": "14:00", "close": "02:00"},
        "wednesday": {"open": "14:00", "close": "02:00"},
        "thursday":  {"open": "14:00", "close": "02:00"},
        "friday":    {"open": "14:00", "close": "02:00"},
        "saturday":  {"open": "14:00", "close": "02:00"},
        "sunday":    {"open": "14:00", "close": "02:00"}
    }'::jsonb,
    'Thanks for calling Meridian Demo Restaurant! We are currently closed. Please call back during business hours.',
    5,
    '["pickup", "delivery"]'::jsonb,
    true,
    NULL,  -- transfer_number — no human handoff in the demo
    true,
    true,
    0.13,  -- Ontario HST (already the schema default but explicit here for clarity)
    true   -- demo_safe: even with a populated pos_access_token, this row never fires a live Square call
)
ON CONFLICT (merchant_id) DO UPDATE SET
    business_name = EXCLUDED.business_name,
    business_type = EXCLUDED.business_type,
    greeting = EXCLUDED.greeting,
    voice = EXCLUDED.voice,
    language = EXCLUDED.language,
    active = EXCLUDED.active,
    menu_items = EXCLUDED.menu_items,
    business_hours = EXCLUDED.business_hours,
    after_hours_message = EXCLUDED.after_hours_message,
    order_types = EXCLUDED.order_types,
    special_instructions_enabled = EXCLUDED.special_instructions_enabled,
    sms_checkout_enabled = EXCLUDED.sms_checkout_enabled,
    sms_ordering_enabled = EXCLUDED.sms_ordering_enabled,
    tax_rate = EXCLUDED.tax_rate,
    demo_safe = EXCLUDED.demo_safe,
    updated_at = now();
    -- phone_number, pos_system, pos_access_token, pos_location_id NOT
    -- updated on conflict — those are owned by the provisioning script
    -- and the Square OAuth flow respectively.
