from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    BOT_TOKEN: str
    SUPER_ADMIN: int

    # Интервалы планировщика (в секундах)
    PARSE_TASK_INTERVAL_SEC: int = 10
    NOTIFY_TASK_INTERVAL_SEC: int = 10

    # Окно актуальности постов для уведомлений (в часах)
    NOTIFY_LOOKBACK_HOURS: int = 24

    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
