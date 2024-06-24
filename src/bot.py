import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from database import (  # Ensure Country is imported
    Country,
    Courier,
    Sender,
    User,
    async_session_maker,
)
from my_keyboards import GeneralCallback, RoleCallback, country_keyboard, role_markup

# Load environment variables from a .env file
load_dotenv()
TOKEN = getenv("BOT_TOKEN")
dp = Dispatcher()


# Handler for the /start command
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


# Handler for the 'sender' role callback
@dp.callback_query(RoleCallback.filter(F.text == "sender"))
async def sender_button_handler(
    callback_query: CallbackQuery, callback_data: RoleCallback
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
        if user is None:
            print(f"User with tg_id {callback_query.message.chat.id} not found")
            return
        try:
            query = insert(Sender).values(user_id=user["id"])
            await session.execute(query)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("Sender already exists")


# Handler for the 'courier' role callback
@dp.callback_query(RoleCallback.filter(F.text == "courier"))
async def courier_button_handler(
    callback_query: CallbackQuery, callback_data: RoleCallback
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
        if user is None:
            print(f"User with tg_id {callback_query.message.chat.id} not found")
            return
        try:
            query = insert(Courier).values(user_id=user["id"])
            await session.execute(query)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            print("Courier already exists")


# Handler for the 'not in the list' callback
@dp.callback_query(GeneralCallback.filter(F.action == "not_in_list"))
async def not_in_list_handler(
    callback_query: CallbackQuery, callback_data: GeneralCallback
):
    direction = callback_data.direction
    await callback_query.message.answer(
        "Свайп на лево и введите название страны отправления"
        if direction == "from"
        else "Свайп на лево и введите название страны прибытия"
    )
    await callback_query.message.delete()


# Handler for processing text input after the "not in the list" callback
@dp.message()
async def text_input_handler(message: Message) -> None:
    if not message.reply_to_message:
        answer = await message.answer("Сделайте свайп по сообщению выше ^^^")
        await message.delete()
        await asyncio.sleep(10)
        await answer.delete()
        return

    if (
        message.reply_to_message.text
        == "Свайп на лево и введите название страны отправления"
    ):
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

        await message.reply_to_message.edit_text(f"Отправить из: {message.text}")
        await message.answer(
            "Отправить в:", reply_markup=await country_keyboard(direction="to")
        )

    if (
        message.reply_to_message.text
        == "Свайп на лево и введите название страны прибытия"
    ):
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

        await message.reply_to_message.edit_text(f"Отправить в: {message.text}")
        await message.answer("Месяц:")

    await message.delete()


# Main function to start the bot
async def main() -> None:
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)


# Entry point for the script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
