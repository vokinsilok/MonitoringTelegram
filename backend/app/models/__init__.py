from backend.app.models.base import Base
from backend.app.models.user import User, UserRole
from backend.app.models.channel import Channel, ChannelProposal
from backend.app.models.keyword import Keyword, KeywordProposal
from backend.app.models.post import Post, PostProcessing
from backend.app.models.message_log import MessageLog
from backend.app.models.telethon_account import TelethonAccount
from backend.app.schemas.post import PostNotification
from backend.app.schemas.message_log import Report

# Экспортируем все модели для удобства импорта
__all__ = [
    'Base',
    'User', 'UserRole',
    'Channel', 'ChannelProposal',
    'Keyword', 'KeywordProposal',
    'Post', 'PostProcessing', 'PostNotification',
    'MessageLog', 'Report',
    'TelethonAccount'
]

