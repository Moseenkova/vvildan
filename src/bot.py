import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from src.config import get_settings
from src.database import (
    User,
    async_session_maker,
    get_or_create,
)
from src.translations import get_welcome_message
from src.utils import (
    create_customer_tg_topic,
    get_customer_chat_id_by_topic_id,
    get_topic_id_by_customer_chat_id,
)

settings = get_settings()
form_router = Router()


@form_router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def command_start_handler(message: Message) -> None:
    user = message.from_user
    language_code = user.language_code if user else None
    full_name = user.full_name if user else message.chat.full_name

    async with async_session_maker() as session:
        await get_or_create(
            session,
            User,
            defaults={"name": full_name},
            tg_id=message.chat.id,
        )

    await message.answer(
        get_welcome_message(
            language_code,
            hbold(full_name),
        )
    )


@form_router.message(Command("id"))
async def command_id(message: Message) -> None:
    await message.answer(
        f"Chat ID: {message.chat.id}\n"
        f"Thread ID: {message.message_thread_id or 'none'}\n"
        f"User ID: {message.from_user.id if message.from_user else 'none'}",
    )


async def get_or_create_customer_topic(message: Message) -> int:
    customer_id = message.chat.id

    topic_id = await get_topic_id_by_customer_chat_id(customer_id)
    if topic_id:
        return topic_id

    user = message.from_user
    display_name = user.full_name if user else str(customer_id)

    topic = await message.bot.create_forum_topic(
        chat_id=settings.SUPPORT_GROUP_ID,
        name=f"{display_name} — {customer_id}",
    )

    topic_id = topic.message_thread_id

    await create_customer_tg_topic(customer_id, topic_id)

    username = f"@{user.username}" if user and user.username else "none"
    await message.bot.send_message(
        chat_id=settings.SUPPORT_GROUP_ID,
        message_thread_id=topic_id,
        text=(
            f"<b>Новое обращение</b>\n"
            f"Имя: {display_name}\n"
            f"Telegram ID: <code>{customer_id}</code>\n"
            f"Username: {username}"
        ),
    )

    return topic_id


@form_router.message(F.chat.type == ChatType.PRIVATE)
async def customer_message(message: Message) -> None:
    if message.from_user and message.from_user.id in settings.SUPPORT_GROUP_ADMIN_IDS:
        return

    topic_id = await get_or_create_customer_topic(message)

    try:
        await message.send_copy(
            chat_id=settings.SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
        )
    except TypeError:
        await message.bot.send_message(
            chat_id=settings.SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
            text="[This message type cannot be copied]",
        )


@form_router.message(F.chat.id == settings.SUPPORT_GROUP_ID)
async def admin_reply(message: Message) -> None:
    if not message.from_user or message.from_user.id not in settings.SUPPORT_GROUP_ADMIN_IDS:
        return

    topic_id = message.message_thread_id
    if topic_id is None:
        return

    customer_id = await get_customer_chat_id_by_topic_id(topic_id)
    if customer_id is None:
        await message.bot.send_message(
            chat_id=settings.SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
            text=f"[topic id {topic_id} not found in db]",
        )
        return

    if message.forum_topic_created or message.forum_topic_closed:
        return

    try:
        await message.send_copy(chat_id=customer_id)
    except TypeError:
        await message.bot.send_message(
            chat_id=customer_id,
            text=message.text or message.caption or "Support sent a message.",
        )


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(form_router)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
