import asyncio
import logging
import sys
from datetime import datetime, timedelta
from os import getenv

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv
from sqlalchemy import insert, select
from sqlalchemy.orm import joinedload

# Ваш код здесь
import database
from database import (
    Country,
    Courier,
    Request,
    Sender,
    User,
    UserCity,
    async_session_maker,
    get_or_create,
)
from my_keyboards import (
    BaggageKindCallback,
    BaggageKinds,
    CancelReqCallback,
    GeneralCallback,
    RoleCallback,
    RoleModelEnum,
    baggage_type_keyboard,
    cancel_req_inline_kb,
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
    period = State()
    message_id = State()
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


@form_router.message(Command("reqs"))
async def command_reqs_handler(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        # Выполняем запрос, чтобы найти все заявки для отправителя

        user = await session.execute(
            select(User).filter(User.tg_id == message.from_user.id)
        )
        user = user.scalars().one_or_none()

        sender_reqs = await session.execute(
            select(Request)
            .options(joinedload(Request.origin))
            .options(joinedload(Request.destination))
            .join(Sender, Sender.id == Request.sender_id)
            .filter(Sender.user_id == user.id)
        )
        sender_reqs = sender_reqs.scalars().all()

        # Get requests where the user is the courier

        if sender_reqs:
            "\n".join(
                [
                    f"From: {req.origin.name}, to: {req.destination.name}, "
                    #    f"period: {req.date.strftime('%Y-%m-%d')} - {req.date.strftime('%Y-%m-%d')}, "
                    f"baggage_types: {req.baggage_types}, "
                    for req in sender_reqs
                ]
            )
            req_dict = {
                req.id: f"From: {req.origin.name}, to: {req.destination.name}, "
                # f"Date: {req.date.strftime('%Y-%m-%d')}, "  исправить на date from и date to
                f"baggage_types: {req.baggage_types}, "
                for req in sender_reqs
            }
            for id in req_dict:
                await message.answer(
                    req_dict[id], reply_markup=cancel_req_inline_kb(id)
                )
        #

        courier_reqs = await session.execute(
            select(Request)
            .options(joinedload(Request.origin))
            .options(joinedload(Request.destination))
            .join(Courier, Courier.id == Request.courier_id)
            .filter(Courier.user_id == user.id)
        )
        courier_reqs = courier_reqs.scalars().all()

        if courier_reqs:
            # Если заявки найдены, отправляем их в виде сообщения
            "\n".join(
                [
                    f"From: {req.origin.name}, to: {req.destination.name}, "
                    f"Date: {req.date.strftime('%Y-%m-%d')}, "
                    f"baggage_types: {req.baggage_types}, "
                    for req in courier_reqs
                ]
            )
            req_dict = {
                req.id: f"From: {req.origin.name}, to: {req.destination.name}, "
                f"Date: {req.date.strftime('%Y-%m-%d')}, "
                f"baggage_types: {req.baggage_types}, "
                for req in courier_reqs
            }
            for id in req_dict:
                await message.answer(
                    req_dict[id], reply_markup=cancel_req_inline_kb(id)
                )


@form_router.callback_query(CancelReqCallback.filter())
async def cancel_request_button_handler(
    callback_query: CallbackQuery,
    callback_data: CancelReqCallback,
) -> None:
    async with async_session_maker() as session:
        # Выполняем запрос для получения объекта Request
        result = await session.execute(
            select(Request).filter(Request.id == callback_data.id)
        )

        # Получаем объект Request из результата
        request = (
            result.scalars().first()
        )  # Используем scalars() для получения первого объекта

        if request:  # Проверяем, существует ли объект
            await session.delete(request)  # Удаляем объект
            await session.commit()  # Подтверждаем изменения в базе данных
    await callback_query.message.delete()


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
        pass
    await state.update_data(city_to_id=user_city.id)
    await state.update_data(city_to_name=message.text)
    data = await state.get_data()
    text = f"Отправить\nИз: {data['city_from_name']}\nВ: {message.text}"
    await bot.edit_message_text(
        text=text, chat_id=message.chat.id, message_id=data["message_id"]
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    await message.delete()
    if data["role"] == RoleModelEnum.courier:
        await state.set_state(Form.date)
        await message.answer("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
    elif data["role"] == RoleModelEnum.sender:
        await state.set_state(Form.period)
        await message.answer(
            "Пожалуйста, введите период в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ."
        )


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


@form_router.message(Form.period)
async def prosses_period(message: Message, state: FSMContext) -> None:
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    await message.delete()
    date_string = message.text.split("-")
    try:
        date_from = datetime.strptime(date_string[0], "%d.%m.%Y")
        date_to = datetime.strptime(date_string[1], "%d.%m.%Y")
    except Exception:
        await state.set_state(Form.period)
        await message.answer(
            f"{message.text} неккоректная дата\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ."
        )
        return

    if date_from > date_to:
        await state.set_state(Form.period)
        await message.answer(
            f"{message.text} неправильно указан период \n Пожалуйста, введите дату в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ."
        )
        return
    if date_from < datetime.now():
        await state.set_state(Form.period)
        await message.answer(
            f"{message.text} неправильно указан период \n Ваша дата из прошлого, введите актуальную дату в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ."
        )
        return
    if date_to > datetime.now() + timedelta(days=60):
        await state.set_state(Form.period)
        await message.answer(
            f"{message.text} неправильно указан период \n Выберите дату на ближайшие 2 месяца в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ."
        )
        return
    data = await state.get_data()
    await state.update_data(date_from=date_string[0], date_to=date_string[1])
    text = f"Отправить\nИз: {data['city_from_name']}\nВ: {data['city_to_name']}\nпериод: {message.text}"
    await bot.edit_message_text(
        text=text, chat_id=message.chat.id, message_id=data["message_id"]
    )
    await state.set_state(Form.baggage_types)

    await message.answer(
        text="Выберите багаж", reply_markup=await baggage_type_keyboard()
    )


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
            f"Отправить\nИз: {data['city_from_name']}\n"
            f"В: {data['city_to_name']}\n"
            + (
                f"дата: {data['date']}\n"
                if data.get("date")
                else f"период: {data['date_from']}-{data['date_to']}\n"
            )
            + f"тип: {chosen_types}"
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
    await state.set_state(Form.comment)


@form_router.message(Form.comment)
async def process_comment(message: Message, state: FSMContext) -> None:
    await state.update_data(comment=message.text)
    data = await state.get_data()
    chosen_types = " ".join([i.value for i in data["baggage_types"]])
    text = (
        f"Отправить\nИз: {data['city_from_name']}\n"
        f"В: {data['city_to_name']}\n"
        + (
            f"дата: {data['date']}\n"
            if data.get("date")
            else f"период: {data['date_from']}-{data['date_to']}\n"
        )
        + f"тип: {chosen_types}"
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
        courier, created = await get_or_create(session, Courier, user_id=user.id)

        if created:
            await callback_query.message.answer("Вы успешно стали курьером!")


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
    date_obj = None
    date_to_obj = None
    date_from_obj = None
    if data.get("date"):
        date_obj = datetime.strptime(data["date"], "%d.%m.%Y").date()
    else:
        date_from_obj = datetime.strptime(data["date_from"], "%d.%m.%Y").date()
        date_to_obj = datetime.strptime(data["date_to"], "%d.%m.%Y").date()
    params = {
        "origin_id": data["city_from_id"],
        "destination_id": data["city_to_id"],
        "date": date_obj,
        "date_from": date_from_obj,
        "date_to": date_to_obj,
        "baggage_types": str([i.name for i in data["baggage_types"]]),
        "status": database.Status.new,
        "comment": data["comment"],
    }
    role = data.get("role")
    # заполняем таблицы реквест (done)
    async with async_session_maker() as session:
        if role == RoleModelEnum.courier:
            query = select(Courier).filter(
                Courier.user.has(tg_id=callback_query.from_user.id)
            )
            result = await session.execute(query)
            courier = result.scalars().one_or_none()
            params["courier_id"] = courier.id
        elif role == RoleModelEnum.sender:
            query = select(Sender).filter(
                Sender.user.has(tg_id=callback_query.from_user.id)
            )
            result = await session.execute(query)
            sender = result.scalars().one_or_none()
            params["sender_id"] = sender.id
        query = insert(Request).values(**params).returning(Request.id)
        result = await session.execute(query)
        request_id = result.scalar()
        await session.commit()
        await state.update_data(request_id=request_id)

    async with async_session_maker() as session:
        if role == RoleModelEnum.sender:
            query = (
                select(Request)
                .options(
                    joinedload(Request.origin),
                    joinedload(Request.destination),
                    joinedload(Request.courier).joinedload(Courier.user),
                )
                .filter(
                    Request.origin_id == params["origin_id"],
                    Request.destination_id == params["destination_id"],
                    Request.date >= params["date_from"],
                    Request.date <= params["date_to"],
                )
            )
        elif role == RoleModelEnum.courier:
            query = (
                select(Request)
                .options(
                    joinedload(Request.origin),
                    joinedload(Request.destination),
                    joinedload(Request.sender).joinedload(Sender.user),
                )
                .filter(
                    Request.origin_id == params["origin_id"],
                    Request.destination_id == params["destination_id"],
                    Request.date_from <= params["date"],
                    Request.date_to >= params["date"],
                )
            )

    result = await session.execute(query)
    requests = result.scalars().all()

    logging.info(str(requests))
    if role == RoleModelEnum.sender:
        for r in requests:
            courier_name = r.courier.user.name
            date_str = r.date.strftime("%d.%m.%Y")
            origin_city = r.origin.name
            destination_city = r.destination.name
            msg = (
                f"Курьер: {courier_name}\n"
                f"Даты: {date_str}\n"
                f"Город отправления: {origin_city}\n"
                f"Город прибытия: {destination_city}\n"
                f"Типы багажа: {r.baggage_types}\n"
                f"Комментарий: {r.comment}"
            )
            await callback_query.message.answer(msg)

    elif role == RoleModelEnum.courier:
        for r in requests:
            sender_name = r.sender.user.name
            date_from_str = r.date_from.strftime("%d.%m.%Y")
            date_to_str = r.date_to.strftime("%d.%m.%Y")
            origin_city = r.origin.name
            destination_city = r.destination.name

            msg = (
                f"Отправитель: {sender_name}\n"
                f"Даты: с {date_from_str} по {date_to_str}\n"
                f"Город отправления: {origin_city}\n"
                f"Город прибытия: {destination_city}\n"
                f"Типы багажа: {r.baggage_types}\n"
                f"Комментарий: {r.comment}"
            )
            await callback_query.message.answer(msg)

    await bot.delete_message(
        callback_query.message.chat.id, callback_query.message.message_id
    )


# после заполнения анкеты для отправителя должен видеть курьер и наооборот


# тип багажа на русский
# разьить по папкам


@form_router.callback_query(CancelReqCallback.filter())
@form_router.callback_query(F.data == "cancel_request")
async def cancel_request_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Запрос отменен.")


@form_router.callback_query(lambda c: c.data.startswith("delete_request:"))
async def delete_request_handler(callback_query: types.CallbackQuery):
    req_id = int(callback_query.data.split(":")[1])  # Получаем ID из callback_data
    async with async_session_maker() as session:
        # Удаляем запрос из базы данных
        await session.execute(select(Request).filter(Request.id == req_id).delete())
        await session.commit()

    await callback_query.answer("Запрос успешно удален.")
    await callback_query.message.edit_text("Запрос удален.")


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
