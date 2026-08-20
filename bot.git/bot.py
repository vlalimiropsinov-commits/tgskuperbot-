# -*- coding: utf-8 -*-
"""
Бот автоматического приёма заявок на вступление в канал/группу.

Что делает:
  1. Ловит событие chat_join_request (кто-то подал заявку).
  2. Ждёт заданную задержку (если настроена).
  3. Одобряет заявку.
  4. По желанию пишет человеку в личку и шлёт тебе уведомление.
  5. Считает статистику в SQLite (/stats).
"""

import asyncio
import html
import logging
import random
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import ChatJoinRequest, Message

import config
import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("approve-bot")

router = Router()


# --------------------------------------------------------------------------
# Главный обработчик: заявка на вступление
# --------------------------------------------------------------------------
@router.chat_join_request()
async def on_join_request(request: ChatJoinRequest, bot: Bot) -> None:
    user = request.from_user
    chat = request.chat
    chat_title = chat.title or str(chat.id)
    who = f"{user.full_name} (@{user.username})" if user.username else user.full_name

    # Фильтр по разрешённым чатам
    if config.ALLOWED_CHATS and chat.id not in config.ALLOWED_CHATS:
        log.warning(
            "Заявка из чата %s (%s) — его нет в ALLOWED_CHATS, пропускаю",
            chat.id,
            chat_title,
        )
        return

    log.info("Новая заявка: %s [id=%s] -> %s [id=%s]", who, user.id, chat_title, chat.id)

    # Задержка, чтобы приём не выглядел роботизированным
    delay = 0
    if config.DELAY_MAX > config.DELAY_MIN:
        delay = random.randint(config.DELAY_MIN, config.DELAY_MAX)
    elif config.DELAY_MIN > 0:
        delay = config.DELAY_MIN
    if delay:
        log.info("Жду %s сек. перед одобрением %s", delay, user.id)
        await asyncio.sleep(delay)

    # Одобрение
    try:
        await request.approve()
    except TelegramRetryAfter as e:
        log.warning("Лимит Telegram, жду %s сек. и пробую снова", e.retry_after)
        await asyncio.sleep(e.retry_after + 1)
        try:
            await request.approve()
        except Exception as e2:  # noqa: BLE001
            log.error("Не удалось одобрить %s после ожидания: %s", user.id, e2)
            storage.log_request(user.id, user.username, user.full_name, chat.id, chat_title, "error")
            return
    except TelegramBadRequest as e:
        # Частые причины: заявку уже обработали вручную, юзер сам отменил,
        # у бота нет права «Добавлять подписчиков».
        log.error("Не удалось одобрить %s: %s", user.id, e.message)
        storage.log_request(user.id, user.username, user.full_name, chat.id, chat_title, "error")
        return
    except Exception as e:  # noqa: BLE001
        log.exception("Неожиданная ошибка при одобрении %s: %s", user.id, e)
        storage.log_request(user.id, user.username, user.full_name, chat.id, chat_title, "error")
        return

    storage.log_request(user.id, user.username, user.full_name, chat.id, chat_title)
    log.info("Заявка одобрена: %s -> %s", who, chat_title)

    # Приветствие в личку (сработает, только если человек когда-то нажимал /start у бота)
    if config.SEND_WELCOME and config.WELCOME_TEXT:
        text = config.WELCOME_TEXT.format(
            name=html.escape(user.first_name or "друг"),
            full_name=html.escape(user.full_name),
            username=("@" + user.username) if user.username else "",
            chat=html.escape(chat_title),
            id=user.id,
        )
        try:
            await bot.send_message(user.id, text)
        except (TelegramForbiddenError, TelegramBadRequest):
            log.info("Личку %s написать нельзя (не запускал бота) — это нормально", user.id)
        except Exception as e:  # noqa: BLE001
            log.warning("Не отправил приветствие %s: %s", user.id, e)

    # Уведомление тебе
    if config.LOG_CHAT_ID:
        mention = f'<a href="tg://user?id={user.id}">{html.escape(user.full_name)}</a>'
        uname = f"@{user.username}" if user.username else "—"
        try:
            await bot.send_message(
                config.LOG_CHAT_ID,
                f"✅ Принят: {mention}\n"
                f"Юзернейм: {html.escape(uname)}\n"
                f"ID: <code>{user.id}</code>\n"
                f"Канал: {html.escape(chat_title)}",
                disable_web_page_preview=True,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("Не смог написать в LOG_CHAT_ID: %s", e)


# --------------------------------------------------------------------------
# Команды в личке бота
# --------------------------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я принимаю заявки на вступление автоматически.\n\n"
        "Чтобы всё заработало:\n"
        "1. Добавь меня админом в канал.\n"
        "2. Дай право <b>«Добавлять подписчиков»</b>.\n"
        "3. В настройках канала включи <b>«Заявки на вступление»</b>.\n\n"
        "Команда /id — узнать ID канала (перешли мне сюда любой пост оттуда)."
    )


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    lines = [f"Твой ID: <code>{message.from_user.id}</code>"]
    origin = getattr(message, "forward_origin", None)
    src = getattr(origin, "chat", None) or getattr(message, "forward_from_chat", None)
    if src is not None:
        lines.append(
            f"ID канала «{html.escape(src.title or '')}»: <code>{src.id}</code>"
        )
    else:
        lines.append("Перешли мне пост из канала — покажу его ID.")
    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if config.ADMINS and message.from_user.id not in config.ADMINS:
        return
    lines = [
        "<b>Статистика</b>",
        f"Принято всего: <b>{storage.total()}</b>",
        f"Принято сегодня: <b>{storage.today()}</b>",
        f"Ошибок: <b>{storage.total('error')}</b>",
    ]
    rows = storage.by_chat()
    if rows:
        lines.append("\nПо каналам:")
        lines += [f"• {html.escape(title)} — {cnt}" for title, cnt in rows]
    await message.answer("\n".join(lines))


# --------------------------------------------------------------------------
# Запуск
# --------------------------------------------------------------------------
async def main() -> None:
    config.validate()
    storage.init(config.DB_PATH)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    log.info("Запущен как @%s (id=%s)", me.username, me.id)
    log.info(
        "Разрешённые чаты: %s",
        ", ".join(map(str, config.ALLOWED_CHATS)) if config.ALLOWED_CHATS else "все",
    )
    log.info("Задержка: %s–%s сек.", config.DELAY_MIN, max(config.DELAY_MIN, config.DELAY_MAX))

    # ВАЖНО: chat_join_request не приходит по умолчанию — его надо явно запросить.
    await bot.delete_webhook(drop_pending_updates=False)
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "chat_join_request", "callback_query"],
        )
    finally:
        storage.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code:
            raise
        log.info("Остановлен")
