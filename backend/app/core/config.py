import os
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Настройки базы данных
    DATABASE_URL: PostgresDsn
    
    # Настройки FastAPI
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Настройки Telegram бота
    BOT_TOKEN: str
    ADMIN_USER_IDS: List[int]
    
    # Настройки мониторинга каналов
    CHANNEL_MONITORING_INTERVAL: int = 300  # Интервал мониторинга в секундах (по умолчанию 5 минут)
    MAX_MONITORING_THREADS: int = 10  # Максимальное количество параллельных потоков для мониторинга и воркеров Telethon
    
    # Настройки сессий Telethon
    SESSION_NAME: str = "telegram_monitoring"  # Базовое имя для сессий Telethon
    
    @field_validator("ADMIN_USER_IDS", mode="before")
    def assemble_admin_ids(cls, v: Union[str, List[int]]) -> List[int]:
        if isinstance(v, str):
            return [int(id_str.strip()) for id_str in v.split(",") if id_str.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
