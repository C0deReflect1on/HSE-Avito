from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas import ModelCreateRequest, ModelResponse, StageUpdateRequest, DownloadResponse
from app import service

router = APIRouter(prefix="/models", tags=["models"])


@router.post("", response_model=ModelResponse, status_code=201)
def register_model(
    name: str = Form(...),
    version: str = Form(...),
    model_type: str = Form(...),
    dataset: str = Form(...),
    owner: str = Form(...),
    params: Optional[str] = Form(None),        # JSON строка
    feature_names: Optional[str] = Form(None),  # JSON строка
    git_path: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    import json
    meta = ModelCreateRequest(
        name=name,
        version=version,
        model_type=model_type,
        dataset=dataset,
        owner=owner,
        params=json.loads(params) if params else None,
        feature_names=json.loads(feature_names) if feature_names else None,
        git_path=git_path,
    )
    return service.register_model(db, meta, file)


@router.get("", response_model=list[ModelResponse])
def search_models(
    name: Optional[str] = Query(None),
    model_type: Optional[str] = Query(None),
    dataset: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return service.search_models(db, name=name, model_type=model_type, dataset=dataset, owner=owner, stage=stage)


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    return service.get_model(db, model_id)


@router.get("/{model_id}/download", response_model=DownloadResponse)
def download_model(model_id: int, db: Session = Depends(get_db)):
    url = service.get_download_url(db, model_id)
    return DownloadResponse(presigned_url=url)


@router.get("/{name}/latest", response_model=ModelResponse)
def get_latest(name: str, stage: str = Query("production"), db: Session = Depends(get_db)):
    return service.get_latest(db, name, stage)


@router.patch("/{model_id}/stage", response_model=ModelResponse)
def update_stage(model_id: int, body: StageUpdateRequest, db: Session = Depends(get_db)):
    return service.update_stage(db, model_id, body)