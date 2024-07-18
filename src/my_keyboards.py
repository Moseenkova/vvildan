from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database import Country, async_session_maker


class DirectionEnum(str, Enum):
    from_ = "from"
    to = "to"


class RoleModelEnum(str, Enum):
    sender = "Sender"
    courier = "Courier"


class RoleCallback(CallbackData, prefix="role"):
    model: RoleModelEnum


class GeneralCallback(CallbackData, prefix="general"):
    text: str


sender_button = InlineKeyboardButton(
    text="Отправитель", callback_data=RoleCallback(model="Sender").pack()
)

courier_button = InlineKeyboardButton(
    text="Курьер", callback_data=RoleCallback(model="Courier").pack()
)

role_markup = InlineKeyboardMarkup(inline_keyboard=[[sender_button, courier_button]])


class CountryCallback(CallbackData, prefix="country"):
    direction: DirectionEnum
    name: str


async def country_keyboard(direction):
    builder = InlineKeyboardBuilder()
    async with async_session_maker() as session:
        query = select(Country.__table__.columns)
        result = await session.execute(query)
        countries = result.mappings().all()

    for country in countries:
        builder.button(
            text=country.name,
            callback_data=CountryCallback(
                direction=f"country_{direction}", name=country.name
            ).pack(),
        )
    builder.button(
        text="Нет в списке",
        callback_data=GeneralCallback(text=f"absent_country_{direction}").pack(),
    )

    return builder.as_markup()
