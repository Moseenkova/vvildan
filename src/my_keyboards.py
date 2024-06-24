from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database import City, Country, async_session_maker


class DirectionEnum(str, Enum):
    from_ = "from"
    to = "to"


class RoleCallback(CallbackData, prefix="role"):
    text: str


class GeneralCallback(CallbackData, prefix="general"):
    text: str


sender_button = InlineKeyboardButton(
    text="Отправитель", callback_data=RoleCallback(text="sender").pack()
)

courier_button = InlineKeyboardButton(
    text="Курьер", callback_data=RoleCallback(text="courier").pack()
)

role_markup = InlineKeyboardMarkup(inline_keyboard=[[sender_button, courier_button]])


class CountryCallback(CallbackData, prefix="country"):
    direction: DirectionEnum
    id: int


class CityCallback(CallbackData, prefix="city"):
    direction: DirectionEnum
    id: int


async def country_keyboard(direction):
    builder = InlineKeyboardBuilder()
    async with async_session_maker() as session:
        query = select(Country.__table__.columns)
        result = await session.execute(query)
        countries = result.mappings().all()

    for country in countries:
        builder.button(
            text=country.name,
            callback_data=CountryCallback(direction=direction, id=country.id).pack(),
        )
    builder.button(
        text="Нет в списке",
        callback_data=GeneralCallback(text=f"absent_country_{direction}").pack(),
    )

    return builder.as_markup()


async def city_keyboard(callback_data):
    builder = InlineKeyboardBuilder()
    async with async_session_maker() as session:
        query = select(City.__table__.columns).filter_by(country_id=callback_data.id)
        result = await session.execute(query)
        cities = result.mappings().all()

    for city in cities:
        builder.button(
            text=city.name,
            callback_data=CityCallback(
                direction=callback_data.direction, id=city.id
            ).pack(),
        )
    builder.button(
        text="Нет в списке",
        callback_data=CityCallback(direction=callback_data.direction, id=0).pack(),
    )

    return builder.as_markup()
