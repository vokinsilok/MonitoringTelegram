import asyncio
import logging
import random
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, UserDeactivatedError, AuthKeyError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message as TelethonMessage, Channel as TelethonChannel

from backend.app.core.config import settings
from backend.app.models.channel import Channel, ChannelStatus
from backend.app.models.post import Post
from backend.app.models.keyword import Keyword
from backend.app.models.telethon_account import TelethonAccount
from backend.app.services.telethon_account_service import TelethonAccountService
from backend.app.services.post_service import create_post
from backend.app.services.post_processing_service import process_post_with_keywords
from backend.app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Максимальное количество потоков для мониторинга
MAX_MONITORING_THREADS = settings.MAX_MONITORING_THREADS


class ChannelMonitoringService:
    """Сервис для мониторинга Telegram-каналов с использованием Telethon"""
    
    def __init__(self):
        self.clients: Dict[int, TelegramClient] = {}  # account_id -> client
        self.active_tasks: Dict[int, asyncio.Task] = {}  # account_id -> task
        self.failed_accounts: Set[int] = set()  # Неудачные аккаунты
        self.monitoring_lock = asyncio.Lock()  # Блокировка для синхронизации мониторинга
        
    async def initialize_client(self, db: AsyncSession, account_id: int) -> Optional[TelegramClient]:
        """Инициализация клиента Telethon для указанного аккаунта"""
        # Получаем аккаунт из БД
        account = await TelethonAccountService.get_account(db, account_id)
        if not account:
            logger.error(f"Аккаунт Telethon с ID {account_id} не найден")
            return None
            
        # Создаем клиент Telethon
        client = TelegramClient(
            f"sessions/{account.name}",  # Путь к файлу сессии
            int(account.api_id),
            account.api_hash
        )
        
        # Сохраняем клиент в словаре
        self.clients[account_id] = client
        
        return client
        
    async def authorize_client(self, db: AsyncSession, account_id: int, code: Optional[str] = None) -> Dict[str, Any]:
        """Авторизация клиента Telethon"""
        # Получаем аккаунт из БД
        account = await TelethonAccountService.get_account(db, account_id)
        if not account:
            return {"success": False, "message": f"Аккаунт Telethon с ID {account_id} не найден"}
            
        # Получаем или создаем клиент
        client = self.clients.get(account_id)
        if not client:
            client = await self.initialize_client(db, account_id)
            if not client:
                return {"success": False, "message": "Не удалось инициализировать клиент Telethon"}
        
        try:
            # Подключаемся к Telegram
            await client.connect()
            
            # Если клиент уже авторизован, обновляем статус в БД
            if await client.is_user_authorized():
                await TelethonAccountService.update_session_info(db, account_id, True)
                return {"success": True, "message": "Клиент уже авторизован"}
                
            # Если нет, запускаем процесс авторизации
            if not code:
                # Отправляем код авторизации на телефон
                await client.send_code_request(account.phone)
                return {
                    "success": True, 
                    "message": f"Код авторизации отправлен на номер {account.phone}",
                    "requires_code": True
                }
            else:
                # Авторизуемся с использованием кода
                await client.sign_in(account.phone, code)
                
                # Обновляем статус в БД
                await TelethonAccountService.update_session_info(db, account_id, True)
                
                return {"success": True, "message": "Авторизация успешно выполнена"}
                
        except SessionPasswordNeededError:
            return {
                "success": False, 
                "message": "Требуется двухфакторная аутентификация. Пожалуйста, используйте метод авторизации с паролем.",
                "requires_2fa": True
            }
        except Exception as e:
            logger.error(f"Ошибка при авторизации клиента Telethon: {str(e)}")
            return {"success": False, "message": f"Ошибка авторизации: {str(e)}"}
            
    async def get_channel_info(self, db: AsyncSession, account_id: int, channel_username: str) -> Dict[str, Any]:
        """Получение информации о канале по его username"""
        # Получаем клиент
        client = self.clients.get(account_id)
        if not client:
            client = await self.initialize_client(db, account_id)
            if not client:
                return {"success": False, "message": "Не удалось инициализировать клиент Telethon"}
                
        try:
            # Подключаемся к Telegram, если еще не подключены
            if not client.is_connected():
                await client.connect()
                
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                return {"success": False, "message": "Клиент не авторизован"}
                
            # Получаем информацию о канале
            entity = await client.get_entity(channel_username)
            
            if isinstance(entity, TelethonChannel):
                return {
                    "success": True,
                    "channel_info": {
                        "id": entity.id,
                        "username": entity.username,
                        "title": entity.title,
                        "participants_count": getattr(entity, "participants_count", None),
                        "about": getattr(entity, "about", None)
                    }
                }
            else:
                return {"success": False, "message": "Указанный username не является каналом"}
                
        except Exception as e:
            logger.error(f"Ошибка при получении информации о канале: {str(e)}")
            return {"success": False, "message": f"Ошибка: {str(e)}"}
            
    async def fetch_channel_posts(
        self, 
        db: AsyncSession, 
        account_id: int, 
        channel_id: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Получение последних сообщений из канала и сохранение их в БД"""
        # Получаем канал из БД
        channel_query = select(Channel).where(Channel.id == channel_id)
        channel_result = await db.execute(channel_query)
        channel = channel_result.scalar_one_or_none()
        
        if not channel:
            return {"success": False, "message": f"Канал с ID {channel_id} не найден"}
            
        # Получаем или инициализируем клиент Telethon
        client = self.clients.get(account_id)
        if not client:
            client = await self.initialize_client(db, account_id)
            if not client:
                return {"success": False, "message": "Не удалось инициализировать клиент Telethon"}
                
        try:
            # Подключаемся к Telegram
            if not client.is_connected():
                await client.connect()
                
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                return {"success": False, "message": "Клиент не авторизован"}
                
            # Получаем информацию о канале
            entity = None
            if channel.username:
                entity = await client.get_entity(channel.username)
            elif channel.channel_id:
                entity = await client.get_entity(channel.channel_id)
            else:
                return {"success": False, "message": "Недостаточно данных для получения информации о канале"}
            
            # Определяем параметры запроса с учетом последнего обработанного сообщения
            min_id = 0
            if channel.last_parsed_message_id:
                min_id = channel.last_parsed_message_id
                
            # Получаем последние сообщения из канала
            messages = await client(GetHistoryRequest(
                peer=entity,
                limit=limit,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=min_id,  # Получаем только новые сообщения
                add_offset=0,
                hash=0
            ))
            
            # Обрабатываем полученные сообщения
            new_posts_count = 0
            max_message_id = channel.last_parsed_message_id or 0
            
            for message in messages.messages:
                # Обновляем максимальный ID сообщения
                if message.id > max_message_id:
                    max_message_id = message.id
                
                # Проверяем, есть ли уже такой пост в БД
                post_query = select(Post).where(
                    Post.channel_id == channel_id,
                    Post.message_id == message.id
                )
                post_result = await db.execute(post_query)
                existing_post = post_result.scalar_one_or_none()
                
                if existing_post:
                    continue  # Пропускаем уже существующие посты
                    
                # Создаем новый пост
                post_data = {
                    "channel_id": channel_id,
                    "message_id": message.id,
                    "content": message.message,
                    "published_at": message.date,
                    "raw_data": str(message.to_dict())
                }
                
                # Сохраняем пост в БД
                post = await create_post(db, post_data)
                new_posts_count += 1
                
                # Получаем все активные ключевые слова
                keywords_query = select(Keyword).where(Keyword.is_active == True)
                keywords_result = await db.execute(keywords_query)
                keywords = keywords_result.scalars().all()
                
                # Проверяем пост на наличие ключевых слов
                if keywords:
                    keyword_texts = [kw.text for kw in keywords]
                    await process_post_with_keywords(db, post.id, keyword_texts)
            
            # Обновляем время последней проверки и ID последнего сообщения
            channel.last_checked = datetime.now()
            if max_message_id > 0 and max_message_id > (channel.last_parsed_message_id or 0):
                channel.last_parsed_message_id = max_message_id
            
            await db.commit()
            
            return {
                "success": True,
                "message": f"Получено {new_posts_count} новых постов из канала {channel.title}",
                "new_posts_count": new_posts_count,
                "last_parsed_message_id": channel.last_parsed_message_id
            }
                
        except Exception as e:
            logger.error(f"Ошибка при получении постов из канала: {str(e)}")
            return {"success": False, "message": f"Ошибка: {str(e)}"} 
            
    async def get_active_accounts(self, db: AsyncSession) -> List[TelethonAccount]:
        """Получение всех активных аккаунтов Telethon"""
        accounts_query = select(TelethonAccount).where(
            TelethonAccount.is_active == True,
            TelethonAccount.is_authorized == True
        )
        accounts_result = await db.execute(accounts_query)
        return list(accounts_result.scalars().all())
    
    async def get_active_channels(self, db: AsyncSession) -> List[Channel]:
        """Получение всех активных каналов для мониторинга"""
        channels_query = select(Channel).where(Channel.status == ChannelStatus.ACTIVE.value)
        channels_result = await db.execute(channels_query)
        return list(channels_result.scalars().all())
    
    async def initialize_account_client(self, db: AsyncSession, account: TelethonAccount) -> Optional[TelegramClient]:
        """Инициализация и подключение клиента Telethon для указанного аккаунта"""
        try:
            # Инициализируем клиент, если его еще нет
            client = self.clients.get(account.id)
            if not client:
                client = await self.initialize_client(db, account.id)
                if not client:
                    error_msg = f"Не удалось инициализировать клиент Telethon для аккаунта {account.id}"
                    logger.error(error_msg)
                    await notification_service.send_account_error_notification(account.id, error_msg)
                    return None
            
            # Подключаемся к Telegram, если еще не подключены
            if not client.is_connected():
                await client.connect()
                
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                error_msg = f"Клиент Telethon для аккаунта {account.id} не авторизован"
                logger.error(error_msg)
                await notification_service.send_account_error_notification(account.id, error_msg)
                return None
                
            # Обновляем время последнего использования аккаунта
            account.last_used = datetime.now()
            await db.commit()
            
            return client
        except (AuthKeyError, UserDeactivatedError) as e:
            error_msg = f"Ошибка авторизации аккаунта {account.id}: {str(e)}"
            logger.error(error_msg)
            # Отмечаем аккаунт как неавторизованный
            account.is_authorized = False
            await db.commit()
            self.failed_accounts.add(account.id)
            await notification_service.send_account_error_notification(account.id, error_msg)
            return None
        except Exception as e:
            error_msg = f"Ошибка при инициализации клиента Telethon для аккаунта {account.id}: {str(e)}"
            logger.error(error_msg)
            self.failed_accounts.add(account.id)
            await notification_service.send_account_error_notification(account.id, error_msg)
            return None
    
    async def monitor_channel_with_account(self, db: AsyncSession, account_id: int, channel_id: int) -> Dict[str, Any]:
        """Мониторинг одного канала с использованием указанного аккаунта"""
        try:
            result = await self.fetch_channel_posts(db, account_id, channel_id)
            # Делаем небольшую паузу между запросами, чтобы не перегружать API
            await asyncio.sleep(1)
            return result
        except FloodWaitError as e:
            logger.warning(f"Ограничение частоты запросов для аккаунта {account_id}. Ожидание: {e.seconds} секунд")
            # Отмечаем аккаунт как неудачный
            self.failed_accounts.add(account_id)
            return {"success": False, "message": f"Ограничение частоты запросов. Ожидание: {e.seconds} секунд"}
        except Exception as e:
            logger.error(f"Ошибка при мониторинге канала {channel_id} с аккаунтом {account_id}: {str(e)}")
            return {"success": False, "message": f"Ошибка: {str(e)}"}
    
    async def monitor_channels(self, db: AsyncSession) -> Dict[str, Any]:
        """Мониторинг всех активных каналов с распределением между аккаунтами"""
        # Блокируем доступ к мониторингу, чтобы не запускать несколько параллельных процессов
        async with self.monitoring_lock:
            # Очищаем список неудачных аккаунтов
            self.failed_accounts.clear()
            
            # Получаем все активные аккаунты
            accounts = await self.get_active_accounts(db)
            if not accounts:
                return {"success": False, "message": "Нет активных аккаунтов Telethon"}
                
            # Получаем все активные каналы
            channels = await self.get_active_channels(db)
            if not channels:
                return {"success": False, "message": "Нет активных каналов для мониторинга"}
            
            # Инициализируем клиенты для всех активных аккаунтов
            active_clients = {}
            for account in accounts:
                client = await self.initialize_account_client(db, account)
                if client:
                    active_clients[account.id] = account
            
            if not active_clients:
                return {"success": False, "message": "Не удалось инициализировать ни один клиент Telethon"}
            
            # Распределяем каналы между аккаунтами
            account_ids = list(active_clients.keys())
            channel_distribution = {}
            
            # Равномерно распределяем каналы между аккаунтами
            for i, channel in enumerate(channels):
                account_id = account_ids[i % len(account_ids)]
                if account_id not in channel_distribution:
                    channel_distribution[account_id] = []
                channel_distribution[account_id].append(channel.id)
            
            # Создаем задачи для мониторинга каналов с ограничением количества параллельных потоков
            results = {}
            total_channels = 0
            total_new_posts = 0
            failed_channels = 0
            
            # Обрабатываем каждый аккаунт и его каналы
            for account_id, channel_ids in channel_distribution.items():
                # Если аккаунт уже в списке неудачных, пропускаем его и перераспределяем каналы
                if account_id in self.failed_accounts:
                    logger.warning(f"Аккаунт {account_id} в списке неудачных, перераспределяем его каналы")
                    # Перераспределяем каналы на другие аккаунты
                    remaining_accounts = [aid for aid in account_ids if aid not in self.failed_accounts]
                    if not remaining_accounts:
                        logger.error("Нет доступных аккаунтов для мониторинга")
                        break
                    
                    # Распределяем каналы этого аккаунта на другие
                    for i, channel_id in enumerate(channel_ids):
                        new_account_id = remaining_accounts[i % len(remaining_accounts)]
                        channel_distribution[new_account_id].append(channel_id)
                    
                    # Пропускаем текущий аккаунт
                    continue
                
                # Обрабатываем каналы текущего аккаунта с ограничением параллельных потоков
                tasks = []
                for channel_id in channel_ids:
                    # Создаем задачу для мониторинга канала
                    task = self.monitor_channel_with_account(db, account_id, channel_id)
                    tasks.append(task)
                    total_channels += 1
                    
                    # Если достигли максимального количества параллельных потоков, ждем завершения
                    if len(tasks) >= MAX_MONITORING_THREADS:
                        # Запускаем задачи и ждем их завершения
                        channel_results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Обрабатываем результаты
                        for result in channel_results:
                            if isinstance(result, Exception):
                                logger.error(f"Ошибка при мониторинге канала: {str(result)}")
                                failed_channels += 1
                            elif result.get("success", False):
                                total_new_posts += result.get("new_posts_count", 0)
                            else:
                                failed_channels += 1
                        
                        # Очищаем список задач
                        tasks = []
                        
                        # Если аккаунт попал в список неудачных, прерываем обработку его каналов
                        if account_id in self.failed_accounts:
                            logger.warning(f"Аккаунт {account_id} добавлен в список неудачных во время мониторинга")
                            break
                
                # Обрабатываем оставшиеся задачи
                if tasks:
                    channel_results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in channel_results:
                        if isinstance(result, Exception):
                            logger.error(f"Ошибка при мониторинге канала: {str(result)}")
                            failed_channels += 1
                        elif result.get("success", False):
                            total_new_posts += result.get("new_posts_count", 0)
                        else:
                            failed_channels += 1
            
            return {
                "success": True,
                "message": f"Мониторинг завершен. Обработано {total_channels} каналов, получено {total_new_posts} новых постов, ошибок: {failed_channels}",
                "total_channels": total_channels,
                "new_posts": total_new_posts,
                "failed_channels": failed_channels
            }


    async def start_periodic_monitoring(self, db: AsyncSession):
        """Запуск периодического мониторинга каналов"""
        logger.info("Запуск периодического мониторинга каналов")
        
        while True:
            try:
                # Запускаем мониторинг всех каналов
                await self.monitor_all_channels(db)
                
                # Ждем указанный интервал перед следующим запуском
                logger.info(f"Ожидание {settings.CHANNEL_MONITORING_INTERVAL} секунд перед следующим мониторингом")
                await asyncio.sleep(settings.CHANNEL_MONITORING_INTERVAL)
                
            except Exception as e:
                error_msg = f"Ошибка при периодическом мониторинге каналов: {str(e)}"
                logger.error(error_msg)
                # Отправляем уведомление о сбое
                await notification_service.send_monitoring_error_notification(error_msg)
                # При ошибке ждем минуту и продолжаем
                await asyncio.sleep(60)  # При ошибке ждем 1 минуту перед повторной попыткой


# Создаем глобальный экземпляр сервиса
channel_monitoring_service = ChannelMonitoringService()
