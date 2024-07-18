import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

import database
from database import (
    Country,
    Courier,
    User,
    UserCity,
    async_session_maker,
    get_or_create,
)
from my_keyboards import (
    DateCallback,
    GeneralCallback,
    RoleCallback,
    country_keyboard,
    month_keyboard,
    months,
    role_markup,
)

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
form_router = Router()


class Form(StatesGroup):
    # TODO keep message text here
    message = State()
    role = State()
    city_from_name = State()
    city_to_name = State()
    city_from_id = State()
    city_to_id = State()
    month = State()
    day = State()
    # TODO delete the last msg and send new instead of editing
    message_id = State()


@form_router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await state.set_data({"name": message.from_user.full_name})
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


@form_router.callback_query(RoleCallback.filter())
async def role_button_handler(
    callback_query: CallbackQuery, callback_data: RoleCallback, state: FSMContext
):
    await state.set_state(Form.city_from_name)
    answer = await callback_query.message.answer(
        "Отправить из:\n(введите название города)"
    )
    await state.set_data({"role": callback_data.model, "message_id": answer.message_id})
    await callback_query.message.delete()
    model = getattr(database, callback_data.model)
    async with async_session_maker() as session:
        user, _ = await get_or_create(
            session,
            User,
            defaults={"name": callback_query.message.chat.full_name},
            tg_id=callback_query.message.chat.id,
        )
        await get_or_create(session, model, user_id=user.id)


@form_router.message(Form.city_from_name)
async def process_city_from(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        user, _ = await get_or_create(
            session,
            User,
            defaults={"name": message.chat.full_name},
            tg_id=message.chat.id,
        )
        user_city, created = await get_or_create(
            session, UserCity, defaults={"created_by_id": user.id}, name=message.text
        )
    if created:
        # TODO: send msg to the team
        ...
    # TODO combine
    await state.update_data(city_from_id=user_city.id)
    await state.update_data(city_from_name=message.text)
    text = f"Отправить\nИз: {message.text}"
    data = await state.get_data()
    await bot.edit_message_text(
        text=text, chat_id=message.chat.id, message_id=data["message_id"]
    )
    await message.delete()
    await state.set_state(Form.city_to_name)
    await message.answer("Отправить в:\n(введите название города)")


@form_router.message(Form.city_to_name)
async def process_city_to(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        user, _ = await get_or_create(
            session,
            User,
            defaults={"name": message.chat.full_name},
            tg_id=message.chat.id,
        )
        user_city, created = await get_or_create(
            session, UserCity, defaults={"created_by_id": user.id}, name=message.text
        )
    if created:
        # TODO: send msg to the team
        ...
    # TODO combine
    await state.update_data(city_to_id=user_city.id)
    await state.update_data(city_to_name=message.text)
    data = await state.get_data()
    text = f"Отправить\nИз: {data['city_from_name']}\nВ: {message.text}"
    await bot.edit_message_text(
        text=text, chat_id=message.chat.id, message_id=data["message_id"]
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    await message.delete()
    await message.answer("Месяц:", reply_markup=await month_keyboard())


@form_router.callback_query(DateCallback.filter())
async def date_button_handler(
    callback_query: CallbackQuery, callback_data: DateCallback, state: FSMContext
):
    data = await state.get_data()
    await state.update_data(month=callback_data.month)
    await callback_query.message.answer("День:")
    await callback_query.message.delete()
    text = f"Отправить\nИз: {data['city_from_name']}\nВ: {data['city_to_name']}\nДата: {months[callback_data.month]}"
    await bot.edit_message_text(
        text=text, chat_id=callback_query.message.chat.id, message_id=data["message_id"]
    )


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


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
