import asyncio
import logging
import re
import sys

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from bot.media import (
    get_transcribable_media,
    media_is_within_duration_limit,
    transcribe_and_translate_media,
)
from bot.translation import needs_translation, translate_topic_text
from bot.translations import get_welcome_message
from bot.utils import (
    create_customer_tg_topic,
    get_customer_topic_by_customer_chat_id,
    get_customer_topic_by_topic_id,
    get_topic_id_by_customer_chat_id,
    update_customer_topic_language,
)
from src.config import Settings, get_settings
from src.database import User, async_session_maker, get_or_create

cfg: Settings = get_settings()
form_router = Router()
TELEGRAM_TEXT_LIMIT = 4096
# Keep download, synchronous OpenAI work, response chaining, and delivery ordered.
_message_translation_lock = asyncio.Lock()


async def send_plain_text(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    message_thread_id: int | None = None,
) -> None:
    for start in range(0, len(text), TELEGRAM_TEXT_LIMIT):
        chunk = text[start : start + TELEGRAM_TEXT_LIMIT]
        if message_thread_id is None:
            await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=None)
        else:
            await bot.send_message(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                text=chunk,
                parse_mode=None,
            )


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


async def get_or_create_customer_topic(message: Message, bot: Bot) -> int:
    customer_id = message.chat.id

    topic_id = await get_topic_id_by_customer_chat_id(customer_id)
    if topic_id:
        return topic_id

    user = message.from_user
    display_name = user.full_name if user else str(customer_id)
    language_code = user.language_code if user else None

    topic = await bot.create_forum_topic(
        chat_id=cfg.SUPPORT_GROUP_ID,
        name=f"{display_name} — {customer_id}",
    )

    topic_id = topic.message_thread_id

    await create_customer_tg_topic(customer_id, topic_id, language_code)

    username = f"@{user.username}" if user and user.username else "none"
    language = language_code or "unknown"
    await bot.send_message(
        chat_id=cfg.SUPPORT_GROUP_ID,
        message_thread_id=topic_id,
        text=(
            f"<b>New support request</b>\n"
            f"Name: {display_name}\n"
            f"Telegram ID: <code>{customer_id}</code>\n"
            f"Username: {username}\n"
            f"Language: {language}"
        ),
    )

    return topic_id


@form_router.message(F.chat.type == ChatType.PRIVATE)
async def customer_message(message: Message, bot: Bot) -> None:
    if message.from_user and message.from_user.id in cfg.SUPPORT_GROUP_ADMIN_IDS:
        return

    topic_id = await get_or_create_customer_topic(message, bot)

    topic = await get_customer_topic_by_customer_chat_id(message.chat.id)
    language_code = topic.language_code if topic else None
    transcribable_media = get_transcribable_media(message)
    if (
        needs_translation(language_code)
        and transcribable_media
        and media_is_within_duration_limit(message)
    ):
        async with _message_translation_lock:
            try:
                original_text, translated = await transcribe_and_translate_media(
                    message,
                    bot,
                    topic_id,
                    source_language=language_code,
                    target_language="ru",
                    direction="customer to support",
                )
            except Exception:
                logging.exception("Could not translate customer media in topic %s", topic_id)
            else:
                await message.send_copy(
                    chat_id=cfg.SUPPORT_GROUP_ID,
                    message_thread_id=topic_id,
                )
                await send_plain_text(
                    bot,
                    cfg.SUPPORT_GROUP_ID,
                    f"{original_text}\n\n{translated}",
                    message_thread_id=topic_id,
                )
                return

    original_text = message.text
    if needs_translation(language_code) and original_text:
        async with _message_translation_lock:
            translated = await translate_topic_text(
                topic_id,
                original_text,
                source_language=language_code,
                target_language="ru",
                direction="customer to support",
            )
            admin_text = f"{original_text}\n\n{translated}"
            await send_plain_text(
                bot,
                cfg.SUPPORT_GROUP_ID,
                admin_text,
                message_thread_id=topic_id,
            )
        return

    try:
        await message.send_copy(
            chat_id=cfg.SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
        )
    except TypeError:
        await bot.send_message(
            chat_id=cfg.SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
            text="[This message type cannot be copied]",
        )


@form_router.message(Command("language"), F.chat.id == cfg.SUPPORT_GROUP_ID)
async def command_language(message: Message, command: CommandObject) -> None:
    if not message.from_user or message.from_user.id not in cfg.SUPPORT_GROUP_ADMIN_IDS:
        return

    topic_id = message.message_thread_id
    if topic_id is None:
        await message.answer("Use /language &lt;code&gt; inside a customer topic.")
        return

    language_code = (command.args or "").strip().lower().replace("_", "-")
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*", language_code):
        await message.answer("Usage: /language &lt;code&gt; (for example, /language en)")
        return

    updated = await update_customer_topic_language(topic_id, language_code)
    if not updated:
        await message.answer(f"Topic <code>{topic_id}</code> was not found in the database.")
        return

    await message.answer(f"Topic language updated to <code>{language_code}</code>.")


@form_router.message(Command("about"), F.chat.id == cfg.SUPPORT_GROUP_ID)
async def command_about(message: Message) -> None:
    if not message.from_user or message.from_user.id not in cfg.SUPPORT_GROUP_ADMIN_IDS:
        return

    await message.answer(
        "<b>Available admin commands</b>\n\n"
        "/about — Show this command list.\n"
        "/id — Show the current chat, topic, and user IDs.\n"
        "/language &lt;code&gt; — Change the customer's language for the current topic "
        "(for example, /language en)."
    )


@form_router.message(F.chat.id == cfg.SUPPORT_GROUP_ID)
async def admin_reply(message: Message, bot: Bot) -> None:
    if not message.from_user or message.from_user.id not in cfg.SUPPORT_GROUP_ADMIN_IDS:
        return

    topic_id = message.message_thread_id
    if topic_id is None:
        return

    topic = await get_customer_topic_by_topic_id(topic_id)
    if topic is None:
        await bot.send_message(
            chat_id=cfg.SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
            text=f"[topic id {topic_id} not found in db]",
        )
        return

    customer_id = topic.customer_chat_id

    if message.forum_topic_created or message.forum_topic_closed:
        return

    transcribable_media = get_transcribable_media(message)
    if (
        needs_translation(topic.language_code)
        and transcribable_media
        and media_is_within_duration_limit(message)
    ):
        async with _message_translation_lock:
            try:
                _, translated = await transcribe_and_translate_media(
                    message,
                    bot,
                    topic_id,
                    source_language="ru",
                    target_language=topic.language_code,
                    direction="support to customer",
                )
            except Exception:
                logging.exception("Could not translate admin media in topic %s", topic_id)
            else:
                await message.send_copy(chat_id=customer_id)
                await send_plain_text(bot, customer_id, translated)
                return

    original_text = message.text
    if needs_translation(topic.language_code) and original_text:
        async with _message_translation_lock:
            translated = await translate_topic_text(
                topic_id,
                original_text,
                source_language="ru",
                target_language=topic.language_code,
                direction="support to customer",
            )
            await send_plain_text(bot, customer_id, translated)
        return

    try:
        await message.send_copy(chat_id=customer_id)
    except TypeError:
        await bot.send_message(
            chat_id=customer_id,
            text=message.text or message.caption or "Support sent a message.",
        )


async def main() -> None:
    bot = Bot(
        token=cfg.BOT_TOKEN.get_secret_value(),
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
