import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from database import Courier, Sender, User, async_session_maker
from my_keyboards import MyCallback, role_markup

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    async with async_session_maker() as session:
        try:
            data = insert(User).values(
                tg_id=message.chat.id, name=message.chat.full_name
            )
            await session.execute(data)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("User already exists")
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}!\nВыбери свою роль.",
        reply_markup=role_markup,
    )


@dp.callback_query(MyCallback.filter(F.text == "sender"))
async def sender_button_handler(query: CallbackQuery, callback_data: MyCallback):
    await query.message.answer("hello")
    async with async_session_maker() as session:
        try:
            data = insert(Sender).values(user_id=query.message.chat.id)
            await session.execute(data)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("sender already exists")

    await query.answer()


@dp.callback_query(MyCallback.filter(F.text == "courier"))
async def courier_button_handler(query: CallbackQuery, callback_data: MyCallback):
    await query.message.answer("hello")
    async with async_session_maker() as session:
        try:
            data = insert(Courier).values(user_id=query.message.chat.id)
            await session.execute(data)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("courier already exists")

    await query.answer()


async def main() -> None:
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
