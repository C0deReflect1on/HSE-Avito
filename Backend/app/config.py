import os

JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_SECONDS: int = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))
