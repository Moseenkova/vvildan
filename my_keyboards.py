from aiogram.filters.callback_data import CallbackData
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup


class MyCallback(CallbackData, prefix="my"):
    text: str


sender_button = InlineKeyboardButton(
    text="Отправитель", callback_data=MyCallback(text="sender").pack()
)
courier_button = InlineKeyboardButton(
    text="Курьер", callback_data=MyCallback(text="courier").pack()
)
role_markup = InlineKeyboardMarkup(inline_keyboard=[[sender_button, courier_button]])
