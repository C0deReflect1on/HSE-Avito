from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

# --- Request schemas ---

class ModelCreateRequest(BaseModel):
    """Метадата при регистрации. Файл идёт отдельным полем multipart."""
    name: str
    version: str
    model_type: str
    dataset: str
    params: Optional[dict[str, Any]] = None
    feature_names: Optional[list[str]] = None
    git_path: Optional[str] = None
    owner: str

class StageUpdateRequest(BaseModel):
    stage: str  # "experimental", "production", "archived"

# --- Response schemas ---

class ModelResponse(BaseModel):
    id: int
    name: str
    version: str
    model_type: str
    dataset: str
    params: Optional[dict[str, Any]] = None
    feature_names: Optional[list[str]] = None
    s3_path: str
    git_path: Optional[str] = None
    stage: str
    owner: str
    created_at: datetime

    class Config:
        from_attributes = True

class DownloadResponse(BaseModel):
    presigned_url: str

class MessageResponse(BaseModel):
    message: str