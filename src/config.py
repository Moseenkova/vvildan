# from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional, final

from pydantic_settings import BaseSettings, SettingsConfigDict


@final
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).resolve().parent.parent / ".env"),),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MODE: Literal["DEV", "TEST", "PROD"] = "DEV"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/courier"
    )
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    ALLOWED_HOSTS: str = "localhost,0.0.0.0,127.0.0.1,test"
    BASE_URL: str = "https://dev.courier.ru"

    SECRET_KEY: str = "xxx"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRES_MINUTES: int = 15 * 24 * 60  # 15 days
    URL_TOKEN_EXPIRE_SECONDS: int = 60 * 60  # 1 hour
    URL_TOKEN_SALT: str = "zzz"

    REFRESH_COOKIE_NAME: str = "refresh"
    SUB: str = "sub"
    EXP: str = "exp"
    IAT: str = "iat"
    JTI: str = "jti"

    BOT_TOKEN: str
    TELEGRAM_SECRET_TOKEN: str = "abcdefghijklmnopqrstuvwxyz"

    DEV_CHAT_ID: str = "5875912525"


# @lru_cache()
def get_settings() -> Settings:
    return Settings()
