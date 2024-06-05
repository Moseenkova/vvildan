from datetime import datetime, timedelta

from aiogram.filters.callback_data import CallbackData
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database import Country, async_session_maker

months = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


class MyCallback(CallbackData, prefix="my"):
    text: str


sender_button = InlineKeyboardButton(
    text="Отправитель", callback_data=MyCallback(text="sender").pack()
)

courier_button = InlineKeyboardButton(
    text="Курьер", callback_data=MyCallback(text="courier").pack()
)

role_markup = InlineKeyboardMarkup(inline_keyboard=[[sender_button, courier_button]])


class CountryCallback(CallbackData, prefix="country"):
    text: str
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
                text=f"country_{direction}", name=country.name
            ).pack(),
        )
    builder.button(
        text="Нет в списке", callback_data=MyCallback(text="absent_country").pack()
    )

    return builder.as_markup()


class DateCallback(CallbackData, prefix="date"):
    text: str
    month: int = 0
    day: int = 0


async def month_keyboard(date):
    builder = InlineKeyboardBuilder()
    today = datetime.today().replace(day=15)
    current_month = today
    next_month = today + timedelta(days=30)
    after_next_month = today + timedelta(days=60)
    builder.button(
        text=months[current_month.month],
        callback_data=DateCallback(
            text=f"month_{date}", month=current_month.month
        ).pack(),
    )
    builder.button(
        text=months[next_month.month],
        callback_data=DateCallback(text=f"month_{date}", month=next_month.month).pack(),
    )
    builder.button(
        text=months[after_next_month.month],
        callback_data=DateCallback(
            text=f"month_{date}", month=after_next_month.month
        ).pack(),
    )

    return builder.as_markup()


async def day_keyboard(date, month):
    builder = InlineKeyboardBuilder()
    today = datetime.today()
    if today.month == month:
        first_day_of_month = today
    else:
        first_day_of_month = today.replace(month=month, day=1)
    days_in_month = []
    current_day = first_day_of_month
    while current_day.month == month:
        days_in_month.append(current_day.day)
        current_day += timedelta(days=1)
    for day in days_in_month:
        builder.button(
            text=str(day),
            callback_data=DateCallback(text=f"day_{date}", day=day).pack(),
        )

    return builder.as_markup()
