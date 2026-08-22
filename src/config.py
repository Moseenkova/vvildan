from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Optional, final

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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

    BOT_TOKEN: SecretStr
    SUPPORT_GROUP_ID: int
    SUPPORT_GROUP_ADMIN_IDS: Annotated[tuple[int, ...], NoDecode]
    TELEGRAM_SECRET_TOKEN: str = "abcdefghijklmnopqrstuvwxyz"

    DEV_CHAT_ID: str = "5875912525"

    @field_validator("SUPPORT_GROUP_ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: object) -> object:
        """Accept a comma-separated list in environment files."""
        if isinstance(value, str):
            return tuple(int(item.strip()) for item in value.split(",") if item.strip())
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
