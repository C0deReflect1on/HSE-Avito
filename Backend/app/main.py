from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers.predict import router as predict_router
from app.services.moderation import ModerationError


app = FastAPI()
app.include_router(predict_router)


@app.get("/")
async def root() -> dict:
    return {"message": "Hello World!"}


@app.exception_handler(ModerationError)
def handle_moderation_error(request: Request, exc: ModerationError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})
