import asyncio
from pathlib import Path
from typing import Dict, List, Set

from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession

# ДАННЫЕ АККАУНТА (из предоставленной строки)
ACCOUNT_NAME = "Основной"
API_ID = 27389530
API_HASH = "aa23880185a29ab93c832e1641f5335f"
PHONE = "+79098447970"
SESSION_STRING = (
    "1ApWapzMBu8F_NO25WeY86B4oEoyPdh5N8RwR86Rqx-mpZrxewjuey6uXSfyvNY_CjEeXqUs-6KX6C1FuCmiEW4BisdIjAy9s78nY4znnS7hGbpmBtdN4fUvp-AFhT_lfhieMwCR5fFVPKG1xIR5C79OVdC31jM9YdRlaaJxBBWIf7OUwXgngTdwn94KMYIwSw2okKaASbk0K1KCbEe-O3961tBIUmkfYDleq3oHFiSoBOzOT3c5CnK5Kebp54C4lc80iY2Jvfbp4nB6_vFPUlsOsJlJKwQ0YTRFZs3lqAJQ48BswAoMyIR9LuTUib24-1efhE5ASWlSKi4ZSZXxNO3rlUp9-smk="
)

# Имя выходного файла
OUTPUT_FILE = Path("channels_links.txt")


def build_link(entity: types.Channel) -> str:
    """Формируем ссылку для канала. Для публичных — https://t.me/username.
    Для приватных — пометка PRIVATE с id."""
    username = getattr(entity, "username", None)
    if username:
        return f"https://t.me/{username}"
    # Приватный/без username — прямую ссылку без прав админа получить нельзя
    cid = getattr(entity, "id", None)
    chat_id_like = f"-100{cid}" if cid is not None else "unknown"
    return f"PRIVATE (chat_id={chat_id_like})"


async def export_links() -> None:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
    await client.connect()
    if not await client.is_user_authorized():
        print("Сессия не авторизована. Обновите строку сессии.")
        return

    # Пытаемся получить названия папок (необязательно)
    folder_titles: Dict[int, str] = {}
    try:
        filters = await client(functions.messages.GetDialogFiltersRequest())
        for f in filters:
            if isinstance(f, types.DialogFilter):
                folder_titles[f.id] = f.title or f"Папка {f.id}"
    except Exception:
        pass

    # Собираем каналы по всем папкам
    lines: List[str] = []
    seen: Set[str] = set()

    # Сначала сгруппируем по folder_id для удобства
    grouped: Dict[int, List[types.Dialog]] = {}
    async for d in client.iter_dialogs():
        if d and d.folder_id and isinstance(d.entity, types.Channel):
            grouped.setdefault(d.folder_id, []).append(d)

    # Если папок нет — всё равно пройдёмся по каналам и выгрузим
    if not grouped:
        async for d in client.iter_dialogs():
            if isinstance(getattr(d, "entity", None), types.Channel):
                ent: types.Channel = d.entity
                link = build_link(ent)
                if link not in seen:
                    seen.add(link)
                    lines.append(link)
    else:
        for fid in sorted(grouped.keys()):
            title = folder_titles.get(fid, f"Папка {fid}")
            lines.append(f"### {title} (id={fid})")
            dialogs = sorted(grouped[fid], key=lambda x: (x.name or "").lower())
            for d in dialogs:
                ent: types.Channel = d.entity
                link = build_link(ent)
                if link not in seen:
                    seen.add(link)
                    lines.append(link)
            lines.append("")  # разделитель

    if lines:
        OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
        print(f"Готово. Ссылки сохранены в {OUTPUT_FILE.resolve()}")
    else:
        print("Каналы не найдены.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(export_links())

