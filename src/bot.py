import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

from database import Country, Courier, Sender, User, async_session_maker, get_or_create
from my_keyboards import GeneralCallback, RoleCallback, country_keyboard, role_markup

# Load environment variables from a .env file
load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
form_router = Router()


class Form(StatesGroup):
    name = State()
    role = State()
    city_from = State()
    city_to = State()
    month_from = State()
    month_to = State()
    day_from = State()
    day_to = State()
    message_id = State()


# Handler for the /start command
@form_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    async with async_session_maker() as session:
        await get_or_create(
            session,
            User,
            defaults={"name": message.chat.full_name},
            tg_id=message.chat.id,
        )
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}!\nВыбери свою роль.",
        reply_markup=role_markup,
    )


# Handler for the 'sender' role callback
@form_router.callback_query(RoleCallback.filter(F.text == "sender"))
async def sender_button_handler(
    callback_query: CallbackQuery, callback_data: RoleCallback
):
    await callback_query.message.answer(
        "Отправить из:", reply_markup=await country_keyboard(direction="from")
    )
    await callback_query.message.delete()
    async with async_session_maker() as session:
        user, _ = await get_or_create(
            session,
            User,
            defaults={"name": callback_query.message.chat.full_name},
            tg_id=callback_query.message.chat.id,
        )
        await get_or_create(session, Sender, user_id=user.id)


# Handler for the 'courier' role callback
@form_router.callback_query(RoleCallback.filter(F.text == "courier"))
async def courier_button_handler(
    callback_query: CallbackQuery, callback_data: RoleCallback
):
    await callback_query.message.answer(
        "Отправить из:", reply_markup=await country_keyboard(direction="from")
    )
    await callback_query.message.delete()
    async with async_session_maker() as session:
        user, _ = await get_or_create(
            session,
            User,
            defaults={"name": callback_query.message.chat.full_name},
            tg_id=callback_query.message.chat.id,
        )
        await get_or_create(session, Courier, user_id=user.id)


@form_router.callback_query(GeneralCallback.filter(F.text == "absent_country_from"))
async def absent_country_from_button_handler(
    callback_query: CallbackQuery, callback_data: GeneralCallback
):
    await callback_query.message.answer(
        "Свайп на лево и введите название страны отправления"
    )
    await callback_query.message.delete()
    await callback_query.answer()


@form_router.callback_query(GeneralCallback.filter(F.text == "absent_country_to"))
async def absent_country_to_button_handler(
    callback_query: CallbackQuery, callback_data: GeneralCallback
):
    await callback_query.message.answer(
        "Свайп на лево и введите название страны прибытия"
    )
    await callback_query.message.delete()
    await callback_query.answer()


# Handler for processing text input after the "not in the list" callback
@form_router.message()
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
            user, _ = await get_or_create(
                session,
                User,
                defaults={"name": message.chat.full_name},
                tg_id=message.chat.id,
            )
            await get_or_create(
                session, Country, defaults={"created_by_id": user.id}, name=message.text
            )

        await message.reply_to_message.edit_text(f"Отправить из: {message.text}")
        await message.answer(
            "Отправить в:", reply_markup=await country_keyboard(direction="to")
        )

    if (
        message.reply_to_message.text
        == "Свайп на лево и введите название страны прибытия"
    ):
        async with async_session_maker() as session:
            user, _ = await get_or_create(
                session,
                User,
                defaults={"name": message.chat.full_name},
                tg_id=message.chat.id,
            )
            await get_or_create(
                session, Country, defaults={"created_by_id": user.id}, name=message.text
            )

        await message.reply_to_message.edit_text(f"Отправить в: {message.text}")
        await message.answer("Месяц:")

    await message.delete()


# Main function to start the bot
async def main() -> None:
    dp = Dispatcher()
    dp.include_router(form_router)
    # Start event dispatching
    await dp.start_polling(bot)


# Entry point for the script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
