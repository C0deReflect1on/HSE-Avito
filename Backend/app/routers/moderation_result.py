from fastapi import APIRouter, HTTPException

from app.repositories.moderation_repository import repository
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()



@router.get("/moderation_result/{task_id}")
async def moderation_result(task_id: int) -> dict:
    logger.info("in moderation_result: %s", task_id)
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

    return resp
