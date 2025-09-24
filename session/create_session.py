
import asyncio
from getpass import getpass
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError, PhoneCodeInvalidError

# Способы задать API:
# 1) через переменные окружения
PHONE = "+79098447970"
API_ID = 27389530            # ваш api_id
API_HASH = "aa23880185a29ab93c832e1641f5335f" # ваш api_hash

async def main():


    phone = PHONE
    api_id = API_ID
    api_hash = API_HASH


    if not phone:
        phone = input("Введите телефон (+79998887766): ").strip()
    if not api_id:
        api_id = int(input("Введите API_ID: ").strip())
    if not api_hash:
        api_hash = input("Введите API_HASH: ").strip()
    # Пустая StringSession => создаём новую авторизацию
    sess = StringSession()
    client = TelegramClient(sess, api_id, api_hash)

    def ask_code() -> str:
        return input("Введите код из Telegram/SMS: ").strip().replace(" ", "")

    await client.connect()
    try:
        # Если уже авторизованы (редкий случай для новой сессии)
        if await client.is_user_authorized():
            session_string = sess.save()
            print("\n=== STRING SESSION (сохраните в надёжном месте) ===")
            print(session_string)
            print("=== КОНЕЦ STRING SESSION ===\n")
            return

        sent = await client.send_code_request(phone)
        phone_code_hash = getattr(sent, "phone_code_hash", None)
        code = ask_code()
        try:
            if phone_code_hash:
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            else:
                await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            # Требуется 2FA пароль
            pw = getpass("Пароль 2FA (если есть, иначе Enter): ")
            await client.sign_in(password=pw)
        except PhoneCodeInvalidError:
            raise RuntimeError("Неверный код подтверждения. Запустите скрипт снова.")
        except PhoneCodeExpiredError:
            raise RuntimeError("Срок действия кода истёк. Запустите скрипт снова и запросите новый код.")

        if not await client.is_user_authorized():
            raise RuntimeError("Авторизация не завершена (is_user_authorized=False)")

        # Получаем строковую сессию
        string_session = sess.save()

        print("\n=== STRING SESSION (сохраните в надёжном месте) ===")
        print(string_session)
        print("=== КОНЕЦ STRING SESSION ===\n")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())