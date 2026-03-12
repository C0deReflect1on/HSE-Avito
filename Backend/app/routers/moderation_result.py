from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_account
from app.repositories.moderation_repository import repository
from app.schemas import Account
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()



@router.get("/moderation_result/{task_id}")
async def moderation_result(
    task_id: int,
    account: Account = Depends(get_current_account),
) -> dict:
    _ = account
    logger.info("in moderation_result: %s", task_id)
    cached_result = await repository.get_cached_task_result(task_id)
    if cached_result is not None:
        return cached_result
    row = await repository.get_by_id(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")

    resp = {
        "task_id": row["id"],
        "status": row["status"],
    }

    # completed -> вернуть результат
    if row["status"] == "completed":
        resp["result"] = {
            "is_violation": row["is_violation"],
            "probability": row["probability"],
        }

    # failed -> вернуть ошибку
    if row["status"] == "failed":
        resp["error_message"] = row["error_message"]

    await repository.cache_task_result(task_id, resp)
    return resp
