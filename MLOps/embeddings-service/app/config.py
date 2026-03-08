from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    model_name: str = os.getenv("MODEL_NAME", "sergeyzh/rubert-mini-frida")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    max_batch_size: int = int(os.getenv("MAX_BATCH_SIZE", "32"))


settings = Settings()
