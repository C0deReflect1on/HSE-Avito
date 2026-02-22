from dataclasses import dataclass
from typing import Any

from app.db import get_pool


@dataclass(frozen=True)
class ItemRepository:
    async def create_item(
        self,
        item_id: int,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> None:
        pool = get_pool()
        await pool.execute(
            """
            INSERT INTO items (id, seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id)
            DO UPDATE SET
                seller_id = EXCLUDED.seller_id,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                images_qty = EXCLUDED.images_qty
            """,
            item_id,
            seller_id,
            name,
            description,
            category,
            images_qty,
        )

    async def get_item_with_user(self, item_id: int) -> dict[str, Any] | None:
        pool = get_pool()
        row = await pool.fetchrow(
            """
            SELECT
                items.id AS item_id,
                items.name,
                items.description,
                items.category,
                items.images_qty,
                users.id AS seller_id,
                users.is_verified_seller
            FROM items
            JOIN users ON users.id = items.seller_id
            WHERE items.id = $1
            """,
            item_id,
        )
        if row is None:
            return None
        return dict(row)

    async def close_item(self, item_id: int) -> bool:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                updated = await conn.fetchval(
                    "UPDATE items SET is_closed = TRUE WHERE id = $1 RETURNING id",
                    item_id,
                )
                if updated is None:
                    return False
                await conn.execute(
                    "DELETE FROM moderation_results WHERE item_id = $1",
                    item_id,
                )
                await conn.execute("DELETE FROM items WHERE id = $1", item_id)
                return True
