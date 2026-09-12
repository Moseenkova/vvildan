from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

import bot.main as bot_main
from bot.utils import create_customer_tg_topic, update_customer_topic_language
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

    assert await update_customer_topic_language(456, "pt-br") is True
    async with async_session_maker() as session:
        updated_topic = await session.scalar(select(CustomerTgTopic))
    assert updated_topic is not None
    assert updated_topic.language_code == "pt-br"

    assert await update_customer_topic_language(999, "en") is False


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


@pytest.mark.asyncio
async def test_admin_can_update_customer_topic_language(monkeypatch) -> None:
    update_language = AsyncMock(return_value=True)
    monkeypatch.setattr(bot_main, "update_customer_topic_language", update_language)

    message = SimpleNamespace(
        from_user=SimpleNamespace(id=bot_main.cfg.SUPPORT_GROUP_ADMIN_IDS[0]),
        message_thread_id=456,
        answer=AsyncMock(),
    )

    await bot_main.command_language(message, SimpleNamespace(args=" PT_br "))

    update_language.assert_awaited_once_with(456, "pt-br")
    message.answer.assert_awaited_once_with("Topic language updated to <code>pt-br</code>.")


@pytest.mark.asyncio
async def test_about_lists_available_admin_commands() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=bot_main.cfg.SUPPORT_GROUP_ADMIN_IDS[0]),
        answer=AsyncMock(),
    )

    await bot_main.command_about(message)

    message.answer.assert_awaited_once()
    command_list = message.answer.await_args.args[0]
    assert "/about" in command_list
    assert "/id" in command_list
    assert "/language &lt;code&gt;" in command_list
