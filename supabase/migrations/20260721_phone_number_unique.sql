-- Defense-in-depth: one agent DID belongs to exactly one merchant.
--
-- Number provisioning is read-then-buy with no DB lock, and config-save used to
-- accept a client-supplied phone_number — either could leave two merchant rows
-- holding the same DID, which makes inbound-call routing (get_merchant_by_phone
-- → first match) nondeterministic. A partial unique index makes a duplicate
-- assignment fail at the database instead of silently corrupting routing.
-- Partial (WHERE phone_number IS NOT NULL) so the many un-provisioned rows
-- (NULL number) are unaffected.

CREATE UNIQUE INDEX IF NOT EXISTS phone_agent_config_phone_number_key
    ON phone_agent_config (phone_number)
    WHERE phone_number IS NOT NULL;
