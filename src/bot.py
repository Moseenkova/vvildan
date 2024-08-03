import asyncio
import logging
import sys
from datetime import datetime, timedelta
from os import getenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
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
from my_keyboards import GeneralCallback, RoleCallback, country_keyboard, role_markup

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
form_router = Router()


class Form(StatesGroup):
    name = State()
    role = State()
    date = State()
    city_from_name = State()
    city_to_name = State()
    city_from_id = State()
    city_to_id = State()
    month_from = State()
    month_to = State()
    day_from = State()
    day_to = State()
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
    await state.update_data(city_to_id=user_city.id)
    await state.update_data(city_to_name=message.text)
    data = await state.get_data()
    text = f"Отправить\nИз: {data['city_from_name']}\nВ: {message.text}"
    await bot.edit_message_text(
        text=text, chat_id=message.chat.id, message_id=data["message_id"]
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    await message.delete()
    await state.set_state(Form.date)
    await message.answer("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")


@form_router.message(Form.date)
async def process_date(message: Message, state: FSMContext) -> None:
    # 1.Неправильно ввел.
    # 2.Формат верный но дата некорректная.
    # 3.Число из прошлого (число меньше текущий даты).
    # 4.Число из будущего (больше двух месяцев).
    # 5.Успешно (число из будущего меньше 2 месяцев).
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    date_string = message.text
    try:
        datetime.strptime(date_string, "%d.%m.%Y")
    except Exception:
        await message.delete()
        await state.set_state(Form.date)
        await message.answer(
            f"{message.text} неккоректная дата\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ."
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


class CallbackContext:
    pass


@form_router.message()
async def text_input_handler(message: Message, state: FSMContext) -> None:
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
        await state.set_state(Form.city_to_name)
        await message.answer(" Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")

    await message.delete()

    def start(update: Update, context: CallbackContext) -> None:
        today = datetime.today()
        two_months_later = today + timedelta(days=60)
        buttons = []

        # Создаем кнопки для каждого дня в пределах двух месяцев
        current_date = today
        while current_date <= two_months_later:
            buttons.append(
                [
                    InlineKeyboardButton(
                        current_date.strftime("%d.%m.%Y"),
                        callback_data=current_date.strftime("%d.%m.%Y"),
                    )
                ]
            )
            current_date += timedelta(days=1)

        reply_markup = InlineKeyboardMarkup(buttons)
        update.message.reply_text(
            "Пожалуйста, выберите дату:", reply_markup=reply_markup
        )

    def button(update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()
        selected_date = query.data
        query.edit_message_text(text=f"Вы выбрали дату: {selected_date}")

    def handle_date_input(update: Update, context: CallbackContext) -> None:
        user_text = update.message.text

        try:
            selected_date = datetime.strptime(user_text, "%d.%m.%Y")
            today = datetime.today()
            two_months_later = today + timedelta(days=60)

            if today <= selected_date <= two_months_later:
                update.message.reply_text(
                    f"Вы выбрали дату: {selected_date.strftime('%d.%m.%Y')}"
                )
            else:
                update.message.reply_text(
                    "Выбранная дата вне допустимого диапазона. Пожалуйста, выберите дату в пределах ближайших двух месяцев."
                )
        except ValueError:
            update.message.reply_text(
                "Неправильный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ."
            )


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
