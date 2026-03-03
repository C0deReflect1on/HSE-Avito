from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routes import router
from app.s3 import ensure_bucket_exists

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket_exists()
    yield

app = FastAPI(title="Model Registry", version="0.1.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}