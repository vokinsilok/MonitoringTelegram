# pip install telethon
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 2040            # ваш api_id
API_HASH = "b18441a1ff607e10a989891a5462e627" # ваш api_hash
SESSION_FILE = "+2349073156748.session" # путь к вашему .session файлу

async def main():
    # Загружаем существующий .session
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()

    # Если сессия не авторизована (редко, но бывает), без кода/логина строку не получить
    if not await client.is_user_authorized():
        print("Сессия не авторизована. Нужна авторизация, иначе String Session не получится.")
        await client.disconnect()
        return

    # Конвертируем SQLite-сессию в строковую
    string_session = StringSession.save(client.session)
    print("Ваш String Session:")
    print(string_session)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())