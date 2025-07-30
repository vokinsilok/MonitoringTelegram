import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.router import api_router
from backend.app.db.database import get_db
from backend.app.services.channel_monitoring_service import channel_monitoring_service

app = FastAPI(
    title="Telegram Channel Monitoring API",
    description="API для системы мониторинга Telegram-каналов",
    version="0.1.0",
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры API
app.include_router(api_router)

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Фоновая задача для периодического мониторинга каналов
@app.on_event("startup")
async def start_monitoring_task():
    """Запуск фоновой задачи для периодического мониторинга каналов"""
    logger.info("Запуск фоновой задачи периодического мониторинга каналов")
    
    # Создаем фоновую задачу
    asyncio.create_task(start_periodic_monitoring())


async def start_periodic_monitoring():
    """Фоновая задача для периодического мониторинга каналов"""
    try:
        # Получаем сессию БД
        async for db in get_db():
            # Запускаем периодический мониторинг
            await channel_monitoring_service.start_periodic_monitoring(db)
            break  # Выходим из цикла после получения сессии
    except Exception as e:
        logger.error(f"Ошибка при запуске периодического мониторинга: {str(e)}")
        # При ошибке пытаемся перезапустить через минуту
        await asyncio.sleep(60)
        asyncio.create_task(start_periodic_monitoring())

@app.get("/")
async def root():
    return {"message": "Telegram Channel Monitoring API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
