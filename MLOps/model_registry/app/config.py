from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://registry:registry@localhost:5432/model_registry"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "models"
    presigned_url_expiry: int = 3600  # секунды

    class Config:
        env_prefix = ""

settings = Settings()