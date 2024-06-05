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
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from database import Country, Courier, Sender, User, async_session_maker
from my_keyboards import (
    CountryCallback,
    DateCallback,
    MyCallback,
    country_keyboard,
    day_keyboard,
    month_keyboard,
    months,
    role_markup,
)

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    async with async_session_maker() as session:
        try:
            query = insert(User).values(
                tg_id=message.chat.id, name=message.chat.full_name
            )
            await session.execute(query)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("User already exists")
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}!\nВыбери свою роль.",
        reply_markup=role_markup,
    )


@dp.callback_query(MyCallback.filter(F.text == "sender"))
async def sender_button_handler(
    callback_query: CallbackQuery, callback_data: MyCallback
):
    await callback_query.message.answer(
        "Отправить из:", reply_markup=await country_keyboard(direction="from")
    )
    await callback_query.message.delete()
    async with async_session_maker() as session:
        query = select(User.__table__.columns).filter_by(
            tg_id=callback_query.message.chat.id
        )
        result = await session.execute(query)
        user = result.mappings().one_or_none()
        try:
            query = insert(Sender).values(user_id=user["id"])
            await session.execute(query)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("sender already exists")

    # await callback_query.answer()


@dp.callback_query(MyCallback.filter(F.text == "absent_country"))
async def absent_country_button_handler(
    callback_query: CallbackQuery, callback_data: MyCallback
):
    await callback_query.message.answer("Свайп на лево и введите название страны")
    await callback_query.answer()


@dp.callback_query(CountryCallback.filter(F.text == "country_from"))
async def country_from_button_handler(
    callback_query: CallbackQuery, callback_data: CountryCallback
):
    await callback_query.message.edit_text(f"Отправить из: {callback_data.name}")
    await callback_query.message.answer(
        "Отправить в:", reply_markup=await country_keyboard(direction="to")
    )


@dp.callback_query(CountryCallback.filter(F.text == "country_to"))
async def country_to_button_handler(
    callback_query: CallbackQuery, callback_data: CountryCallback
):
    await callback_query.message.edit_text(f"Отправить в: {callback_data.name}")
    await callback_query.message.answer(
        "Месяц:", reply_markup=await month_keyboard(date="from")
    )


@dp.callback_query(DateCallback.filter(F.text == "month_from"))
async def country_button_handler(
    callback_query: CallbackQuery, callback_data: DateCallback
):
    await callback_query.message.edit_text(f"Дата: {months[callback_data.month]}")
    await callback_query.message.answer(
        "День:", reply_markup=await day_keyboard(date="from", month=callback_data.month)
    )


@dp.message()
async def echo_handler(message: Message) -> None:
    if not message.reply_to_message:
        return

    if message.reply_to_message.text == "Свайп на лево и введите название страны":
        async with async_session_maker() as session:
            query = select(User.__table__.columns).filter_by(tg_id=message.chat.id)
            result = await session.execute(query)
            user = result.mappings().one_or_none()
            try:
                query = insert(Country).values(
                    name=message.text, created_by_id=user["id"]
                )
                await session.execute(query)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                print("Country already exists")


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
