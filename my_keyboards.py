import asyncio
import logging
import sys
from os import getenv
from typing import Optional

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.types.callback_query import CallbackQuery
from aiogram.filters.callback_data import CallbackData
from dotenv import load_dotenv


class MyCallback(CallbackData, prefix="my"):
    text: str


sender_button = InlineKeyboardButton(text="Отправитель", 
                                     callback_data=MyCallback(text="sender").pack())
courier_button = InlineKeyboardButton(text="Курьер", 
                                      callback_data=MyCallback(text="courier").pack())
role_markup = InlineKeyboardMarkup(inline_keyboard=[[sender_button, courier_button]])



