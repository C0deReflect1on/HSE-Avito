import asyncio

import pytest

from app import db
from app.repositories.items import ItemRepository
from app.repositories.moderation_repository import ModerationRepository
from app.repositories.users import UserRepository
from app.schemas import SimplePredictRequest
from app.storage.memory import InMemoryStorage

pytestmark = pytest.mark.integration


def test_repositories_create_and_read_item(database_dsn):
    async def _run():
        await db.connect(database_dsn)
        users = UserRepository()
        items = ItemRepository()
        await users.create_user(1, True)
        await items.create_item(10, 1, "Item", "Description", 2, 1)
        row = await items.get_item_with_user(10)
        await db.disconnect()
        return row

    row = asyncio.run(_run())
    assert row is not None
    assert row["item_id"] == 10
    assert row["seller_id"] == 1


def test_moderation_repository_lifecycle(database_dsn):
    async def _run():
        await db.connect(database_dsn)
        users = UserRepository()
        items = ItemRepository()
        moderation = ModerationRepository(InMemoryStorage())
        await users.create_user(2, False)
        await items.create_item(20, 2, "Item", "Description", 3, 2)
        task_id = await moderation.create_pending(SimplePredictRequest(item_id=20))
        await moderation.update_completed(task_id, is_violation=True, probability=0.9)
        row = await moderation.get_by_id(task_id)
        await db.disconnect()
        return row

    row = asyncio.run(_run())
    assert row is not None
    assert row["status"] == "completed"
    assert row["is_violation"] is True


def test_close_item_deletes_item_and_moderation_rows(database_dsn):
    async def _run():
        await db.connect(database_dsn)
        users = UserRepository()
        items = ItemRepository()
        moderation = ModerationRepository(InMemoryStorage())
        await users.create_user(3, True)
        await items.create_item(30, 3, "Item", "Description", 4, 0)
        task_id = await moderation.create_pending(SimplePredictRequest(item_id=30))
        closed = await items.close_item(30)
        item_row = await items.get_item_with_user(30)
        moderation_row = await moderation.get_by_id(task_id)
        await db.disconnect()
        return closed, item_row, moderation_row

    closed, item_row, moderation_row = asyncio.run(_run())
    assert closed is True
    assert item_row is None
    assert moderation_row is None
