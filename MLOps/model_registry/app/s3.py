import boto3
from app.config import settings

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )

def ensure_bucket_exists():
    """Создать бакет если не существует. Вызывать при старте приложения."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket)

def build_s3_key(name: str, version: str) -> str:
    """Детерминированный путь: models/{name}/{version}/model.bin"""
    return f"models/{name}/{version}/model.bin"

def upload_file(s3_key: str, file_bytes: bytes):
    client = get_s3_client()
    client.put_object(Bucket=settings.s3_bucket, Key=s3_key, Body=file_bytes)

def generate_presigned_url(s3_key: str) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=settings.presigned_url_expiry,
    )