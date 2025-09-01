from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from app.core.logging import main_logger
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db
from bot.utils.db_manager import DBManager

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

router = Router()


class TelethonAddForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_api_id = State()
    waiting_for_api_hash = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()


def _normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "")
    if not phone.startswith("+"):
        # На всякий случай добавим +, если пользователь ввёл без него
        if phone.startswith("8"):
            phone = "+7" + phone[1:]
        elif phone.isdigit():
            phone = "+" + phone
    return phone


@router.message(F.text.startswith("🔐 Добавить Telethon"))
async def start_add_telethon(message: Message, state: FSMContext):
    async with get_atomic_db() as db:
        perms = await UserService(db).cheek_user_permissions(message.from_user.id)
    if not perms.get("is_admin"):
        await message.answer("Нет прав. Только администратор может добавлять Telethon-аккаунт.")
        return
    await message.answer("Введите имя аккаунта (произвольное):")
    await state.set_state(TelethonAddForm.waiting_for_name)


@router.message(TelethonAddForm.waiting_for_name)
async def telethon_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введите api_id (число из https://my.telegram.org):")
    await state.set_state(TelethonAddForm.waiting_for_api_id)


@router.message(TelethonAddForm.waiting_for_api_id)
async def telethon_api_id(message: Message, state: FSMContext):
    try:
        api_id = int(message.text.strip())
    except ValueError:
        await message.answer("api_id должно быть числом. Повторите ввод:")
        return
    await state.update_data(api_id=api_id)
    await message.answer("Введите api_hash (строка из https://my.telegram.org):")
    await state.set_state(TelethonAddForm.waiting_for_api_hash)


@router.message(TelethonAddForm.waiting_for_api_hash)
async def telethon_api_hash(message: Message, state: FSMContext):
    api_hash = message.text.strip()
    if len(api_hash) < 10:
        await message.answer("Похоже, api_hash некорректен. Повторите ввод:")
        return
    await state.update_data(api_hash=api_hash)
    await message.answer("Введите номер телефона в международном формате (например, +79991234567):")
    await state.set_state(TelethonAddForm.waiting_for_phone)


@router.message(TelethonAddForm.waiting_for_phone)
async def telethon_phone(message: Message, state: FSMContext):
    phone = _normalize_phone(message.text)
    await state.update_data(phone=phone)

    data = await state.get_data()
    api_id = data["api_id"]
    api_hash = data["api_hash"]

    # Отправляем код подтверждения
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        await client.send_code_request(phone)
        await client.disconnect()
        await message.answer("Мы отправили код подтверждения в Telegram. Введите код (5 цифр):")
        await state.set_state(TelethonAddForm.waiting_for_code)
    except Exception as e:
        main_logger.error(f"telethon send_code_request error: {e}")
        await message.answer("Не удалось отправить код. Проверьте api_id/api_hash/номер и попробуйте снова. Введите номер повторно:")
        await state.set_state(TelethonAddForm.waiting_for_phone)


@router.message(TelethonAddForm.waiting_for_code)
async def telethon_code(message: Message, state: FSMContext):
    code = message.text.strip().replace(" ", "")
    data = await state.get_data()
    name = data["name"]
    api_id = data["api_id"]
    api_hash = data["api_hash"]
    phone = data["phone"]

    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await client.connect()
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            # Нужен пароль 2FA
            await client.disconnect()
            await state.update_data(pending_code=code)
            await message.answer("Для входа требуется пароль (2FA). Введите пароль:")
            await state.set_state(TelethonAddForm.waiting_for_password)
            return

        # Успешный вход, сохраняем сессию
        session_string = client.session.save()
        await _persist_telethon_account(message, name, api_id, api_hash, phone, session_string)
        await message.answer("✅ Telethon-аккаунт добавлен и авторизован.")
    except Exception as e:
        main_logger.error(f"telethon sign_in error: {e}")
        await message.answer("Неверный код или ошибка авторизации. Отправьте номер телефона ещё раз:")
        await state.set_state(TelethonAddForm.waiting_for_phone)
    finally:
        await client.disconnect()


@router.message(TelethonAddForm.waiting_for_password)
async def telethon_password(message: Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    name = data["name"]
    api_id = data["api_id"]
    api_hash = data["api_hash"]
    phone = data["phone"]
    code = data.get("pending_code")

    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await client.connect()
        # Сначала пытаемся войти по паролю 2FA (аккаунт уже привязан к номеру)
        await client.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        try:
            await client.sign_in(password=password)
            session_string = client.session.save()
            await _persist_telethon_account(message, name, api_id, api_hash, phone, session_string)
            await message.answer("✅ Telethon-аккаунт добавлен и авторизован.")
        except Exception as e:
            main_logger.error(f"telethon 2FA error: {e}")
            await message.answer("Неверный пароль. Попробуйте ещё раз. Введите пароль 2FA:")
            return
    except Exception as e:
        main_logger.error(f"telethon final sign_in error: {e}")
        await message.answer("Ошибка авторизации. Начнём заново. Введите номер телефона:")
        await state.set_state(TelethonAddForm.waiting_for_phone)
    finally:
        await client.disconnect()
        await state.update_data(pending_code=None)


async def _persist_telethon_account(message: Message, name: str, api_id: int, api_hash: str, phone: str, session_string: str):
    async with get_atomic_db() as db:
        # Пишем/обновляем запись
        existing = await db.telethon.get_by_filter(phone=phone)
        values = {
            "name": name,
            "api_id": str(api_id),
            "api_hash": api_hash,
            "phone": phone,
            "description": None,
            "is_active": True,
            "is_authorized": True,
            "session_string": session_string,
        }
        if existing:
            await db.telethon.update_account(existing.id, values)
        else:
            await db.telethon.create_account(values)

