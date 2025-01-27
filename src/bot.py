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
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv
from sqlalchemy import insert

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
    BaggageKindCallback,
    BaggageKinds,
    GeneralCallback,
    RoleCallback,
    baggage_type_keyboard,
    country_keyboard,
    final_keyboard,
    role_markup,
)

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
    # TODO message_text
    baggage_types = State()
    extra = State()
    comment = State()


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


@form_router.callback_query(GeneralCallback.filter(F.text == "start_button"))
async def start_button_handler(
    callback_query: CallbackQuery, callback_data: GeneralCallback, state: FSMContext
) -> None:
    print("ghcghh")
    await state.set_data({"name": callback_query.from_user.full_name})

    await callback_query.message.answer(
        text=f"Привет, {hbold(callback_query.from_user.full_name)}!\nВыбери свою роль.",
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
    # TODO нельзя что бы из и в города были одинаковы
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


# TODO добавить данные о дате в форму
@form_router.message(Form.date)
async def process_date(message: Message, state: FSMContext) -> None:
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    await message.delete()
    date_string = message.text
    try:
        user_datetime = datetime.strptime(date_string, "%d.%m.%Y")
    except Exception:
        await state.set_state(Form.date)
        await message.answer(
            f"{message.text} неккоректная дата\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ."
        )
        return
    if user_datetime < datetime.now():
        await state.set_state(Form.date)
        await message.answer(
            f"{message.text} неккоректная дата\nВаша дата из прошлого, введите актуальную дату"
        )
        return
    if user_datetime > datetime.now() + timedelta(days=60):
        await state.set_state(Form.date)
        await message.answer(
            f"{message.text} неккоректная дата\nВыберите дату на ближайшие 2 месяца"
        )
        return
    data = await state.get_data()
    await state.update_data(date=message.text)
    text = f"Отправить\nИз: {data['city_from_name']}\nВ: {data['city_to_name']}\nдата: {message.text}"
    await bot.edit_message_text(
        text=text, chat_id=message.chat.id, message_id=data["message_id"]
    )
    await state.set_state(Form.baggage_types)

    await message.answer(
        text="Выберите багаж", reply_markup=await baggage_type_keyboard()
    )


# TODO aiogram test
@form_router.callback_query(BaggageKindCallback.filter())
async def baggage_kind_button_handler(
    callback_query: CallbackQuery, callback_data: BaggageKindCallback, state: FSMContext
):
    data = await state.get_data()
    baggage_types = data.get("baggage_types", [])
    if baggage_types == [] and callback_data.kind == BaggageKinds.finish:
        await callback_query.answer(text="выберите вид багажа", show_alert=True)
        return

    if callback_data.kind == BaggageKinds.finish:
        chosen_types = " ".join([i.value for i in baggage_types])
        text = (
            f"Отправить\nИз: {data['city_from_name']}"
            f"\nВ: {data['city_to_name']}"
            f"\nдата: {data['date']}"
            f"\nтип: {chosen_types}"
        )
        await bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
        )
        await bot.edit_message_text(
            text=text,
            chat_id=callback_query.message.chat.id,
            message_id=data["message_id"],
        )
        await callback_query.message.answer(text="Добавьте описания багажа")
        await state.set_state(Form.comment)

        return

    if callback_data.kind in baggage_types:
        await callback_query.answer(
            text=f"{callback_data.kind.value} уже выбран", show_alert=True
        )
        return

    await callback_query.message.delete()

    baggage_types.append(callback_data.kind)
    await state.update_data(baggage_types=baggage_types)
    chosen_types = " ".join([i.value for i in baggage_types])
    await callback_query.message.answer(
        text=f"{chosen_types}\nВыберите багаж, выберите необходимое и после нажмите готово",
        reply_markup=await baggage_type_keyboard(),
    )
    await state.set_state(Form.extra)


@form_router.message(Form.baggage_types)
async def process_baggage_type(message: Message, state: FSMContext) -> None:
    await message.answer("Пожалуйста, добавьте описания багажа:")
    await state.set_state(Form.comment)  # Переход к состоянию ожидания комментария.


@form_router.message(Form.comment)
async def process_comment(message: Message, state: FSMContext) -> None:
    await state.update_data(comment=message.text)
    data = await state.get_data()
    chosen_types = " ".join([i.value for i in data["baggage_types"]])
    text = (
        f"Отправить\nИз: {data['city_from_name']}"
        f"\nВ: {data['city_to_name']}"
        f"\nдата: {data['date']}"
        f"\nтип: {chosen_types}"
        f"\nкомментарий: {message.text}"
    )
    await bot.edit_message_text(
        text=text, chat_id=message.chat.id, message_id=data["message_id"]
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    await message.delete()

    await message.answer("Проверьте данные", reply_markup=await final_keyboard())


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


@form_router.callback_query(GeneralCallback.filter(F.text == "finish_button"))
async def command_finish_handler(
    callback_query: CallbackQuery, callback_data: GeneralCallback, state: FSMContext
) -> None:
    data = await state.get_data()
    date_str = data["date"]
    date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
    async with async_session_maker() as session:
        params = {
            "origin_id": data["city_from_id"],
            "destination_id": data["city_to_id"],
            "date": date_obj,
            "baggage_types": str([i.name for i in data["baggage_types"]]),
            "status": database.Status.new,
            "comment": data["comment"],
        }
        role = data.get("role")
        if role == "courier":
            params["courier_id"] = callback_query.from_user.id
        elif role == "sender":
            params["sender_id"] = callback_query.from_user.id
        query = insert(database.Request).values(**params).returning(database.Request)
        await session.execute(query)
        await session.commit()
    await callback_query.answer()


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

# создать миграции (revision)
# прменить миграции (upgrade head)
