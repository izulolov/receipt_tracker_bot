from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str

    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    DB_ECHO: bool = False
    
    # Добавляем поддержку переменных PostgreSQL/Нужен для Docker
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # File upload settings
    UPLOAD_DIR: Path = Path("uploads")
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB

    # OCR settings
    OCR_ENABLED: bool = True
    TESSERACT_CMD: Optional[str] = None

    # Receipt settings
    MAX_RECEIPTS_PER_PAGE: int = 5
    RECEIPT_PREVIEW_LENGTH: int = 100

    # Team settings
    MAX_TEAM_NAME_LENGTH: int = 50
    MAX_TEAM_MEMBERS: int = 10
    INVITE_LINK_EXPIRE_HOURS: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Добавляем эту строку для игнорирования лишних переменных


settings = Settings()

# Create upload directory if it doesn't exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)