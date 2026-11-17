from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(repr=False)
    redis_url: str
    admin_email: str
    admin_password: str = Field(repr=False)
    cookie_secure: bool = False
    session_ttl_seconds: int = 28800
