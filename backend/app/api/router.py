from fastapi import APIRouter

from backend.app.api import users, channels, keywords, posts, logs, telethon_accounts, monitoring

# Создаем главный роутер API
api_router = APIRouter(prefix="/api")

# Подключаем все роутеры
api_router.include_router(users.router)
api_router.include_router(channels.router)
api_router.include_router(keywords.router)
api_router.include_router(posts.router)
api_router.include_router(logs.router)
api_router.include_router(telethon_accounts.router)
api_router.include_router(monitoring.router)
