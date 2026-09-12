from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

import bot.main as bot_main
from bot.utils import create_customer_tg_topic
from src.database import CustomerTgTopic, async_session_maker


@pytest.mark.asyncio
async def test_create_customer_tg_topic_saves_language_code(database) -> None:
    await create_customer_tg_topic(123, 456, "id")

    async with async_session_maker() as session:
        topic = await session.scalar(select(CustomerTgTopic))

    assert topic is not None
    assert topic.customer_chat_id == 123
    assert topic.topic_id == 456
    assert topic.language_code == "id"


@pytest.mark.asyncio
async def test_new_customer_topic_uses_telegram_user_language(monkeypatch) -> None:
    monkeypatch.setattr(
        bot_main,
        "get_topic_id_by_customer_chat_id",
        AsyncMock(return_value=None),
    )
    create_topic_record = AsyncMock(return_value=456)
    monkeypatch.setattr(bot_main, "create_customer_tg_topic", create_topic_record)

    message = SimpleNamespace(
        chat=SimpleNamespace(id=123),
        from_user=SimpleNamespace(
            full_name="Test User",
            username="test_user",
            language_code="id",
        ),
    )
    bot = SimpleNamespace(
        create_forum_topic=AsyncMock(return_value=SimpleNamespace(message_thread_id=456)),
        send_message=AsyncMock(),
    )

    topic_id = await bot_main.get_or_create_customer_topic(message, bot)

    assert topic_id == 456
    create_topic_record.assert_awaited_once_with(123, 456, "id")
