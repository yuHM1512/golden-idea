import json
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/golden_idea"
    SQLALCHEMY_ECHO: bool = False

    # FastAPI
    API_TITLE: str = "Golden Idea Web App"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # JWT (TODO: Enable when implementing password-based auth)
    # JWT_ALGORITHM: str = "HS256"
    # JWT_EXPIRATION_HOURS: int = 24

    # File Upload
    UPLOAD_DIR: str = str(_BACKEND_DIR / "uploads")
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "mp4", "avi", "mov"]

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        case_sensitive=True,
    )

    @field_validator("ALLOWED_EXTENSIONS", "CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_list_env(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            return value
        if not isinstance(value, str):
            return value

        raw = value.strip()
        if raw == "":
            return []

        if raw.startswith("[") or raw.startswith("{"):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return parsed

        return [item.strip() for item in raw.split(",") if item.strip()]

    @field_validator("UPLOAD_DIR", mode="before")
    @classmethod
    def _resolve_upload_dir(cls, value):
        if value is None:
            return str(_BACKEND_DIR / "uploads")
        if not isinstance(value, str):
            return value
        raw = value.strip()
        if raw == "":
            return str(_BACKEND_DIR / "uploads")
        path = Path(raw)
        if not path.is_absolute():
            path = _BACKEND_DIR / path
        return str(path.resolve())

settings = Settings()
