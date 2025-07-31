import os
from typing import List, Optional, Union, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Режим работы
    MODE: Literal["TEST", "LOCAL", "DEV", "PROD"]
    
    # Настройки базы данных
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    
    # Настройки FastAPI
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BACKEND_PORT: int = 8000
    
    # Настройки Telegram бота
    BOT_TOKEN: str
    ADMIN_USER_IDS: str
    
    # Настройки мониторинга каналов
    CHANNEL_MONITORING_INTERVAL: int = 300  # Интервал мониторинга в секундах (по умолчанию 5 минут)
    MAX_MONITORING_THREADS: int = 10  # Максимальное количество параллельных потоков для мониторинга
    
    # Настройки сессий Telethon
    SESSION_NAME: str = "telegram_monitoring"  # Базовое имя для сессий Telethon
    
    @property
    def redis_url(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"
    
    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def get_admin_ids(self) -> List[int]:
        """Получить список ID администраторов в виде списка целых чисел"""
        if not self.ADMIN_USER_IDS:
            return []
        return [int(id_str.strip()) for id_str in self.ADMIN_USER_IDS.split(",") if id_str.strip()]
    
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
