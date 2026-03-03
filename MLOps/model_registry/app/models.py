from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class ModelRecord(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    dataset = Column(String, nullable=False)
    params = Column(JSONB, nullable=True)
    feature_names = Column(JSONB, nullable=True)
    s3_path = Column(String, nullable=False)
    git_path = Column(String, nullable=True)
    stage = Column(String, nullable=False, default="experimental")
    owner = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_name_version"),
    )