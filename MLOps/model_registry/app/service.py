from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, UploadFile

from app.models import ModelRecord
from app.schemas import ModelCreateRequest, StageUpdateRequest
from app import s3

# Допустимые переходы стадий
ALLOWED_TRANSITIONS = {
    "experimental": "production",
    "production": "archived",
}

def register_model(db: Session, meta: ModelCreateRequest, file: UploadFile) -> ModelRecord:
    """Регистрация модели: запись в БД + загрузка файла в S3.
    
    Идемпотентность: если name+version уже есть — 409.
    Консистентность: сначала S3, потом БД. Если БД упадёт — в S3 останется мусор,
    но не будет ситуации "запись есть, файла нет".
    """
    existing = db.query(ModelRecord).filter_by(name=meta.name, version=meta.version).first()
    if existing:
        raise HTTPException(status_code=409, detail="Model with this name+version already exists")

    s3_key = s3.build_s3_key(meta.name, meta.version)
    file_bytes = file.file.read()

    # Сначала загружаем в S3
    s3.upload_file(s3_key, file_bytes)

    # Потом пишем в БД
    record = ModelRecord(
        name=meta.name,
        version=meta.version,
        model_type=meta.model_type,
        dataset=meta.dataset,
        params=meta.params,
        feature_names=meta.feature_names,
        s3_path=s3_key,
        git_path=meta.git_path,
        stage="experimental",
        owner=meta.owner,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def search_models(
    db: Session,
    name: str | None = None,
    model_type: str | None = None,
    dataset: str | None = None,
    owner: str | None = None,
    stage: str | None = None,
    feature_names: list[str] | None = None,
) -> list[ModelRecord]:
    """Поиск по произвольной комбинации параметров."""
    query = db.query(ModelRecord)

    if name:
        query = query.filter(ModelRecord.name == name)
    if model_type:
        query = query.filter(ModelRecord.model_type == model_type)
    if dataset:
        query = query.filter(ModelRecord.dataset == dataset)
    if owner:
        query = query.filter(ModelRecord.owner == owner)
    if stage:
        query = query.filter(ModelRecord.stage == stage)
    if feature_names:
        # jsonb contains: feature_names содержит все указанные
        query = query.filter(ModelRecord.feature_names.contains(feature_names))

    return query.order_by(desc(ModelRecord.created_at)).all()


def get_model(db: Session, model_id: int) -> ModelRecord:
    record = db.query(ModelRecord).filter_by(id=model_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")
    return record


def get_download_url(db: Session, model_id: int) -> str:
    record = get_model(db, model_id)
    return s3.generate_presigned_url(record.s3_path)


def get_latest(db: Session, name: str, stage: str = "production") -> ModelRecord:
    """Последняя версия модели по имени и стадии."""
    record = (
        db.query(ModelRecord)
        .filter_by(name=name, stage=stage)
        .order_by(desc(ModelRecord.created_at))
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail=f"No {stage} model found with name '{name}'")
    return record


def update_stage(db: Session, model_id: int, req: StageUpdateRequest) -> ModelRecord:
    record = get_model(db, model_id)

    allowed_next = ALLOWED_TRANSITIONS.get(record.stage)
    if allowed_next != req.stage:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{record.stage}' to '{req.stage}'. "
                   f"Allowed: '{record.stage}' → '{allowed_next}'"
        )

    record.stage = req.stage
    db.commit()
    db.refresh(record)
    return record