import asyncio
import logging
import sys
from os import getenv
from typing import Any, Dict

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()
TOKEN = getenv("BOT_TOKEN")
form_router = Router()


class Form(StatesGroup):
    name = State()
    role = State()
    city = State()
    city_from_id = State()
    city_to_id = State()
    month_from = State()
    month_to = State()
    day_from = State()
    day_to = State()


@form_router.message(CommandStart())
async def command_start(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.name)

    await message.answer(
        " Эй, как тебя звай?",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("cancel"))
@form_router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state is None:
        return
    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Cancelled.",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Form.name)
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(Form.role)
    await message.answer(
        f"Мне приятный. Здравствуй {html.quote(message.text)}!\nВыбери свою роль?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Курьер"),
                    KeyboardButton(text="Отправитель"),
                ]
            ],
            resize_keyboard=True,
        ),
    )


@form_router.message(Form.role, F.text.casefold() == "отправитель")
async def process_sender_role(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await message.answer(
        "Not bad not terrible.\nSee you soon.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await show_summary(message=message, data=data, positive=False)


@form_router.message(Form.role, F.text.casefold() == "курьер")
async def process_courier_role(message: Message, state: FSMContext) -> None:
    await state.update_data(role=message.text)
    await state.set_state(Form.city)
    await message.reply(
        "Отправить из:\nвведите название города",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Form.role)
async def process_unknown_role(message: Message) -> None:
    await message.reply("I don't understand you :(")


@form_router.message(Form.city)
async def process_city(message: Message, state: FSMContext) -> None:
    data = await state.update_data(city=message.text)
    await state.clear()
    if message.text.casefold() == "python":
        await message.reply(
            "Python, you say? That's the city that makes my circuits light up! 😉"
        )
    await show_summary(message=message, data=data)


async def show_summary(
    message: Message, data: Dict[str, Any], positive: bool = True
) -> None:
    name = data["name"]
    city = data.get("city", "<something unexpected>")
    text = f"I'll keep in mind that, {html.quote(name)}, "
    text += (
        f"you like to write bots with {html.quote(city)}."
        if positive
        else "you don't like to write bots, so sad..."
    )
    await message.answer(text=text, reply_markup=ReplyKeyboardRemove())


async def main():
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(form_router)
    # Start event dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
