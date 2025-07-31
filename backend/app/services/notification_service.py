import logging
import httpx
from typing import List, Optional

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Сервис для отправки уведомлений о сбоях и важных событиях"""
    
    @staticmethod
    async def send_telegram_notification(message: str, admin_ids: Optional[List[int]] = None) -> bool:
        """
        Отправка уведомления через Telegram-бота администраторам
        
        Args:
            message: Текст сообщения
            admin_ids: Список ID администраторов для отправки (если None, то всем администраторам)
        
        Returns:
            bool: Успешность отправки
        """
        try:
            # Если не указаны конкретные администраторы, отправляем всем
            if admin_ids is None:
                admin_ids = settings.get_admin_ids()
                
            if not admin_ids:
                logger.warning("Нет администраторов для отправки уведомлений")
                return False
                
            # Формируем базовый URL для API Telegram
            base_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
            
            # Отправляем сообщение каждому администратору
            async with httpx.AsyncClient() as client:
                for admin_id in admin_ids:
                    params = {
                        "chat_id": admin_id,
                        "text": f"🚨 УВЕДОМЛЕНИЕ О СБОЕ 🚨\n\n{message}",
                        "parse_mode": "HTML"
                    }
                    
                    response = await client.post(base_url, params=params)
                    
                    if response.status_code != 200:
                        logger.error(f"Ошибка при отправке уведомления администратору {admin_id}: {response.text}")
                        
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {str(e)}")
            return False
    
    @staticmethod
    async def send_monitoring_error_notification(error_message: str) -> bool:
        """
        Отправка уведомления о сбое мониторинга
        
        Args:
            error_message: Текст сообщения об ошибке
            
        Returns:
            bool: Успешность отправки
        """
        message = f"<b>Сбой в системе мониторинга каналов</b>\n\n"
        message += f"<i>Описание ошибки:</i>\n{error_message}\n\n"
        message += f"<i>Время:</i> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return await NotificationService.send_telegram_notification(message)
    
    @staticmethod
    async def send_account_error_notification(account_id: int, error_message: str) -> bool:
        """
        Отправка уведомления о сбое аккаунта Telethon
        
        Args:
            account_id: ID аккаунта
            error_message: Текст сообщения об ошибке
            
        Returns:
            bool: Успешность отправки
        """
        message = f"<b>Сбой аккаунта Telethon</b>\n\n"
        message += f"<i>ID аккаунта:</i> {account_id}\n"
        message += f"<i>Описание ошибки:</i>\n{error_message}\n\n"
        message += f"<i>Время:</i> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return await NotificationService.send_telegram_notification(message)


# Создаем глобальный экземпляр сервиса
notification_service = NotificationService()
