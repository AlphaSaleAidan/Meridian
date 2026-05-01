"""
Sync Repository — Bulk upserts and POS connection management.

Used by the sync engine and workers for writing data from POS systems.
"""
import json
import logging

logger = logging.getLogger("meridian.db.sync_repo")


class SyncRepo:
    """Bulk sync operations against the connection pool."""

    def __init__(self, pool):
        self._pool = pool

    async def upsert_locations(self, org_id: str, locations: list[dict]) -> int:
        if not locations:
            return 0

        async with self._pool.acquire() as conn:
            count = 0
            for loc in locations:
                await conn.execute(
                    """
                    INSERT INTO locations (
                        id, org_id, name, is_primary, address_line1, city,
                        state, zip_code, latitude, longitude, phone,
                        business_hours, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        address_line1 = EXCLUDED.address_line1,
                        city = EXCLUDED.city,
                        state = EXCLUDED.state,
                        zip_code = EXCLUDED.zip_code,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        phone = EXCLUDED.phone,
                        business_hours = EXCLUDED.business_hours,
                        is_active = EXCLUDED.is_active
                    """,
                    loc["id"], org_id, loc.get("name", ""),
                    loc.get("is_primary", False),
                    loc.get("address_line1"), loc.get("city"),
                    loc.get("state"), loc.get("zip_code"),
                    loc.get("latitude"), loc.get("longitude"),
                    loc.get("phone"),
                    json.dumps(loc.get("business_hours", {})),
                    loc.get("is_active", True),
                )
                count += 1

            logger.info(f"Upserted {count} locations for org {org_id}")
            return count

    async def upsert_categories(self, org_id: str, categories: list[dict]) -> int:
        if not categories:
            return 0

        async with self._pool.acquire() as conn:
            count = 0
            for cat in categories:
                await conn.execute(
                    """
                    INSERT INTO product_categories (id, org_id, name, external_id, is_active)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (org_id, external_id) WHERE external_id IS NOT NULL
                    DO UPDATE SET name = EXCLUDED.name, is_active = EXCLUDED.is_active
                    """,
                    cat["id"], org_id, cat.get("name", ""),
                    cat.get("external_id"), cat.get("is_active", True),
                )
                count += 1

            logger.info(f"Upserted {count} categories for org {org_id}")
            return count

    async def upsert_products(self, org_id: str, products: list[dict]) -> int:
        if not products:
            return 0

        async with self._pool.acquire() as conn:
            count = 0
            for p in products:
                await conn.execute(
                    """
                    INSERT INTO products (
                        id, org_id, category_id, external_id, name, description,
                        sku, barcode, price_cents, has_variants, variant_of,
                        variant_attrs, is_active, is_taxable, image_url, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                        $12::jsonb, $13, $14, $15, $16::jsonb
                    )
                    ON CONFLICT (org_id, external_id) WHERE external_id IS NOT NULL
                    DO UPDATE SET
                        name = EXCLUDED.name, description = EXCLUDED.description,
                        sku = EXCLUDED.sku, barcode = EXCLUDED.barcode,
                        price_cents = EXCLUDED.price_cents,
                        is_active = EXCLUDED.is_active, image_url = EXCLUDED.image_url,
                        metadata = products.metadata || EXCLUDED.metadata
                    """,
                    p["id"], org_id, p.get("category_id"),
                    p.get("external_id"), p.get("name", ""),
                    p.get("description"), p.get("sku"), p.get("barcode"),
                    p.get("price_cents", 0), p.get("has_variants", False),
                    p.get("variant_of"),
                    json.dumps(p.get("variant_attrs", {})),
                    p.get("is_active", True), p.get("is_taxable", True),
                    p.get("image_url"),
                    json.dumps(p.get("metadata", {})),
                )
                count += 1

            logger.info(f"Upserted {count} products for org {org_id}")
            return count

    async def upsert_transactions_batch(
        self,
        org_id: str,
        transactions: list[dict],
        items: list[dict],
    ) -> tuple[int, int]:
        if not transactions:
            return 0, 0

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                txn_count = 0
                for txn in transactions:
                    await conn.execute(
                        """
                        INSERT INTO transactions (
                            id, org_id, location_id, pos_connection_id, external_id,
                            type, subtotal_cents, tax_cents, tip_cents, discount_cents,
                            total_cents, payment_method, employee_name, employee_external_id,
                            transaction_at, metadata
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6::transaction_type,
                            $7, $8, $9, $10, $11,
                            $12::payment_method, $13, $14, $15, $16::jsonb
                        )
                        ON CONFLICT (org_id, external_id)
                        DO UPDATE SET
                            total_cents = EXCLUDED.total_cents,
                            tax_cents = EXCLUDED.tax_cents,
                            tip_cents = EXCLUDED.tip_cents,
                            discount_cents = EXCLUDED.discount_cents,
                            payment_method = EXCLUDED.payment_method,
                            employee_name = EXCLUDED.employee_name,
                            metadata = transactions.metadata || EXCLUDED.metadata
                        """,
                        txn["id"], org_id, txn.get("location_id"),
                        txn.get("pos_connection_id"), txn.get("external_id"),
                        txn.get("type", "sale"),
                        txn.get("subtotal_cents", 0), txn.get("tax_cents", 0),
                        txn.get("tip_cents", 0), txn.get("discount_cents", 0),
                        txn.get("total_cents", 0),
                        txn.get("payment_method", "other"),
                        txn.get("employee_name"), txn.get("employee_external_id"),
                        txn.get("transaction_at"),
                        json.dumps(txn.get("metadata", {})),
                    )
                    txn_count += 1

                item_count = 0
                for item in items:
                    await conn.execute(
                        """
                        INSERT INTO transaction_items (
                            id, transaction_id, transaction_at, org_id,
                            product_id, product_name, quantity,
                            unit_price_cents, total_cents, discount_cents,
                            modifiers, metadata
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                            $11::jsonb, $12::jsonb
                        )
                        ON CONFLICT (id, transaction_at)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            total_cents = EXCLUDED.total_cents,
                            discount_cents = EXCLUDED.discount_cents
                        """,
                        item["id"], item["transaction_id"],
                        item.get("transaction_at"), org_id,
                        item.get("product_id"), item.get("product_name", ""),
                        item.get("quantity", 1),
                        item.get("unit_price_cents", 0),
                        item.get("total_cents", 0),
                        item.get("discount_cents", 0),
                        json.dumps(item.get("modifiers", {})),
                        json.dumps(item.get("metadata", {})),
                    )
                    item_count += 1

        logger.info(
            f"Upserted {txn_count} transactions, {item_count} items for org {org_id}"
        )
        return txn_count, item_count

    async def upsert_inventory_snapshots(
        self, org_id: str, snapshots: list[dict]
    ) -> int:
        if not snapshots:
            return 0

        async with self._pool.acquire() as conn:
            count = 0
            for snap in snapshots:
                await conn.execute(
                    """
                    INSERT INTO inventory_snapshots (
                        id, org_id, location_id, product_id,
                        quantity_on_hand, quantity_sold, quantity_received,
                        quantity_wasted, snapshot_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (id, snapshot_at)
                    DO UPDATE SET
                        quantity_on_hand = EXCLUDED.quantity_on_hand,
                        quantity_sold = EXCLUDED.quantity_sold,
                        quantity_received = EXCLUDED.quantity_received,
                        quantity_wasted = EXCLUDED.quantity_wasted
                    """,
                    snap["id"], org_id, snap.get("location_id"),
                    snap.get("product_id"),
                    snap.get("quantity_on_hand", 0),
                    snap.get("quantity_sold", 0),
                    snap.get("quantity_received", 0),
                    snap.get("quantity_wasted", 0),
                    snap.get("snapshot_at"),
                )
                count += 1

            logger.info(f"Upserted {count} inventory snapshots for org {org_id}")
            return count

    # ─── POS Connection Management ────────────────────────────

    async def upsert_pos_connection(self, connection: dict) -> str:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO pos_connections (
                    id, org_id, location_id, provider, status,
                    access_token_enc, refresh_token_enc, token_expires_at,
                    external_merchant_id, external_location_id, metadata
                ) VALUES ($1, $2, $3, 'square', $4, $5, $6, $7, $8, $9, $10::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    access_token_enc = EXCLUDED.access_token_enc,
                    refresh_token_enc = EXCLUDED.refresh_token_enc,
                    token_expires_at = EXCLUDED.token_expires_at
                RETURNING id
                """,
                connection["id"], connection["org_id"],
                connection.get("location_id"),
                connection.get("status", "connected"),
                connection.get("access_token_enc"),
                connection.get("refresh_token_enc"),
                connection.get("token_expires_at"),
                connection.get("external_merchant_id"),
                connection.get("external_location_id"),
                json.dumps(connection.get("metadata", {})),
            )

    async def update_connection_sync_status(
        self,
        connection_id: str,
        status: str,
        last_sync_status: str | None = None,
        historical_complete: bool | None = None,
    ):
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE pos_connections SET
                    status = $2,
                    last_sync_at = NOW(),
                    last_sync_status = COALESCE($3, last_sync_status),
                    historical_import_complete = COALESCE($4, historical_import_complete),
                    historical_import_completed_at = CASE
                        WHEN $4 = TRUE THEN NOW()
                        ELSE historical_import_completed_at
                    END
                WHERE id = $1
                """,
                connection_id, status, last_sync_status, historical_complete,
            )

    async def get_active_connections(self) -> list:
        return await self._pool.fetch(
            """
            SELECT * FROM pos_connections
            WHERE provider = 'square'
              AND status = 'connected'
              AND historical_import_complete = TRUE
            ORDER BY last_sync_at ASC NULLS FIRST
            """
        )

    async def get_connections_needing_refresh(self) -> list:
        return await self._pool.fetch(
            """
            SELECT * FROM pos_connections
            WHERE provider = 'square'
              AND status IN ('connected', 'syncing')
              AND token_expires_at < NOW() + INTERVAL '5 days'
            """
        )
