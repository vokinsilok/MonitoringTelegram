import pytz
from datetime import datetime

from app.core.config import settings
from bot.utils.db_manager import DBManager


class BaseService:
    db: DBManager | None

    def __init__(self, db: DBManager | None = None) -> None:
        self.db = db

    @classmethod
    def get_moscow_time(cls):
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz).replace(tzinfo=None)
        return moscow_time


