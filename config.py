# -*- coding: utf-8 -*-
"""Настройки бота. Всё читается из файла .env — код трогать не нужно."""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env берём из папки со скриптом, а не из текущей директории терминала.
# utf-8-sig — чтобы BOM от Блокнота не приклеился к первой переменной.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, encoding="utf-8-sig")


def _get_str(key: str, default: str = "") -> str:
    value = os.getenv(key)
    return default if value is None else value.strip()


def _get_int(key: str, default: int) -> int:
    raw = _get_str(key)
    if not raw:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    raw = _get_str(key).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "y", "on", "да")


def _get_int_list(key: str) -> list[int]:
    raw = _get_str(key)
    if not raw:
        return []
    result = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


BOT_TOKEN: str = _get_str("BOT_TOKEN")

# ID каналов/групп, которые бот обслуживает. Пусто = обслуживать все, куда его добавили.
ALLOWED_CHATS: list[int] = _get_int_list("ALLOWED_CHATS")

# ID твоих аккаунтов — им доступны /stats и /id.
ADMINS: list[int] = _get_int_list("ADMINS")

# Задержка перед одобрением в секундах (0 = мгновенно).
# Если DELAY_MAX > DELAY_MIN — задержка выбирается случайно в этом диапазоне.
DELAY_MIN: int = _get_int("DELAY_MIN", 0)
DELAY_MAX: int = _get_int("DELAY_MAX", 0)

# Писать ли новому подписчику в личку после одобрения.
SEND_WELCOME: bool = _get_bool("SEND_WELCOME", True)
WELCOME_TEXT: str = _get_str(
    "WELCOME_TEXT",
    "Привет, {name}! Твоя заявка в «{chat}» одобрена. Добро пожаловать!",
)

# Куда слать уведомления о новых заявках (ID чата или твой ID). Пусто = не слать.
LOG_CHAT_ID: int = _get_int("LOG_CHAT_ID", 0)

# Файл базы данных со статистикой.
DB_PATH: str = _get_str("DB_PATH", "bot.db")


def validate() -> None:
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN пустой. Открой файл .env и вставь токен от @BotFather."
        )
    if ":" not in BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN выглядит неправильно (нет двоеточия). Проверь .env."
        )
