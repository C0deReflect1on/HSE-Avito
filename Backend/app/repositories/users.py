from dataclasses import dataclass
from typing import Any

from app.db import get_pool


@dataclass(frozen=True)
class UserRepository:
    async def create_user(self, user_id: int, is_verified_seller: bool) -> None:
        pool = get_pool()
        await pool.execute(
            """
            INSERT INTO users (id, is_verified_seller)
            VALUES ($1, $2)
            ON CONFLICT (id)
            DO UPDATE SET is_verified_seller = EXCLUDED.is_verified_seller
            """,
            user_id,
            is_verified_seller,
        )

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT id, is_verified_seller FROM users WHERE id = $1", user_id
        )
        if row is None:
            return None
        return dict(row)
