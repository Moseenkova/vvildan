import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

from database import (
    User,
    async_session_maker,
    get_or_create,
)
from translations import get_welcome_message

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
