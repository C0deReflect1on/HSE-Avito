import asyncio

import pytest

from app import db
from app.repositories.items import ItemRepository
from app.repositories.users import UserRepository

pytestmark = pytest.mark.integration


def test_create_user_and_item(database_dsn):
    async def _run():
        await db.connect(database_dsn)
        user_repo = UserRepository()
        item_repo = ItemRepository()

        await user_repo.create_user(42, True)
        await item_repo.create_item(
            item_id=1001,
            seller_id=42,
            name="Item",
            description="Description",
            category=2,
            images_qty=3,
        )
        item = await item_repo.get_item_with_user(1001)
        await db.disconnect()
        return item

    item = asyncio.run(_run())
    assert item is not None
    assert item["item_id"] == 1001
    assert item["seller_id"] == 42
    assert item["is_verified_seller"] is True
