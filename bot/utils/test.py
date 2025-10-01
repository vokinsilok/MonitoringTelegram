
import asyncio
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout


# ДАННЫЕ ДЛЯ ОДНОРАЗОВОГО ЗАПУСКА
BOT_TOKEN = "8035753211:AAFgpEJDcYgprjIIC3zKkcJ6ksmdxVOu4WY"
USERS: List[int] = [
    5566931873]
DEPTH = 4000           # сколько сообщений назад пытаться удалять
PAUSE_SECONDS = 0.03   # пауза между удалениями
REQUEST_TIMEOUT = 5 # тайм-аут запроса к Telegram API (сек)
PROGRESS_EVERY = 0.5   # как часто печатать прогресс


async def purge_chat_history(
    bot: Bot,
    chat_id: int,
    start_from_message_id: int,
    depth: int = DEPTH,
    pause: float = PAUSE_SECONDS,
    request_timeout: float = REQUEST_TIMEOUT,
    progress_every: int = PROGRESS_EVERY,
) -> int:
    deleted = 0
    low = max(1, start_from_message_id - depth)
    for mid in range(start_from_message_id, low - 1, -1):
        try:
            await bot.delete_message(chat_id, mid, request_timeout=request_timeout)
            deleted += 1
            if progress_every and (deleted % progress_every == 0):
                print(f"[progress] chat={chat_id} deleted={deleted}/{start_from_message_id - low + 1}")
            if pause:
                await asyncio.sleep(pause)
        except TelegramRetryAfter as e:
            wait_s = getattr(e, "retry_after", 1.0) + 0.5
            print(f"[rate-limit] chat={chat_id} mid={mid} wait={wait_s:.1f}s")
            await asyncio.sleep(wait_s)
        except TelegramBadRequest:
            # Слишком старое/не своё/не найдено — пропускаем
            continue
        except asyncio.TimeoutError:
            print(f"[timeout] chat={chat_id} mid={mid} -> skip")
            continue
        except asyncio.CancelledError:
            # Бывает от aiohttp при сетевых сбоях — подождать и продолжить
            print(f"[cancelled] chat={chat_id} mid={mid} -> retry later")
            await asyncio.sleep(1.0)
            continue
        except Exception as e:
            print(f"[warn] chat={chat_id} mid={mid} err={e}")
            continue
    return deleted


async def run_once() -> None:
    # Сессия с тайм-аутом, чтобы не подвисать на запросах
    session = AiohttpSession(timeout=ClientTimeout(total=REQUEST_TIMEOUT))
    bot = Bot(token=BOT_TOKEN, session=session)
    print("START")
    try:
        for cid in sorted(set(USERS)):
            print(f"[start] chat={cid}")
            try:
                marker = await bot.send_message(cid, "Очистка сообщений бота…", request_timeout=REQUEST_TIMEOUT)
                print(f"[marker] chat={cid} mid={marker.message_id}")
            except Exception as e:
                print(f"[skip] chat={cid} не удалось отправить маркер: {e}")
                continue

            try:
                deleted = await purge_chat_history(
                    bot=bot,
                    chat_id=cid,
                    start_from_message_id=marker.message_id,
                    depth=DEPTH,
                    pause=PAUSE_SECONDS,
                    request_timeout=REQUEST_TIMEOUT,
                    progress_every=PROGRESS_EVERY,
                )
                # Пытаемся удалить служебный маркер
                try:
                    await bot.delete_message(cid, marker.message_id, request_timeout=REQUEST_TIMEOUT)
                except Exception:
                    pass
                print(f"[done] chat={cid} удалено сообщений: {deleted}")
            except Exception as e:
                print(f"[error] chat={cid} ошибка очистки: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_once())