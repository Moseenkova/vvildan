from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.auth.utils import create_token_pair
from src.database import RequestRole
from src.main import app
from src.messages.service import notify_message_recipient
from tests.conftest import AuthenticatedClient
from tests.factories import FactoryNamespace


async def _matching_requests(auth_ac, factory):
    recipient = await factory.User(tg_id=7002, name="Courier", username="courier")
    departure = await factory.City(name="Jakarta")
    arrival = await factory.City(name="Singapore")
    own = await factory.Request(
        user=auth_ac.current_user,
        role=RequestRole.sender,
        date_from=date(2026, 9, 12),
        date_to=date(2026, 9, 14),
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    matching = await factory.Request(
        user=recipient,
        role=RequestRole.courier,
        date_from=date(2026, 9, 13),
        date_to=date(2026, 9, 13),
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    return recipient, own, matching


@pytest.mark.asyncio
async def test_match_message_creates_dialog_and_unread_message(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipient, own, matching = await _matching_requests(auth_ac, factory)
    notify = AsyncMock()
    monkeypatch.setattr("src.messages.service.notify_message_recipient", notify)

    response = await auth_ac.client.post(
        "/api/messages/from-match",
        json={
            "own_request_id": own.id,
            "matching_request_id": matching.id,
            "body": "Can you carry documents?",
        },
    )

    assert response.status_code == 201
    dialog = response.json()
    assert dialog["other_user"] == {"name": "Courier", "username": "courier"}
    assert dialog["messages"][0]["body"] == "Can you carry documents?"
    assert dialog["messages"][0]["is_mine"] is True
    notify.assert_awaited_once()

    recipient_token = create_token_pair(recipient)["access"]["token"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers = {"Authorization": f"Bearer {recipient_token}"}
        dialogs_response = await client.get("/api/messages")
        assert dialogs_response.status_code == 200
        assert dialogs_response.json()[0]["unread_count"] == 1

        messages_response = await client.get(f"/api/messages/{dialog['id']}")
        assert messages_response.status_code == 200
        assert messages_response.json()["messages"][0]["is_read"] is True

        dialogs_response = await client.get("/api/messages")
        assert dialogs_response.json()[0]["unread_count"] == 0


@pytest.mark.asyncio
async def test_dialog_reply_is_unread_for_other_user(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipient, own, matching = await _matching_requests(auth_ac, factory)
    monkeypatch.setattr("src.messages.service.notify_message_recipient", AsyncMock())
    created = await auth_ac.client.post(
        "/api/messages/from-match",
        json={
            "own_request_id": own.id,
            "matching_request_id": matching.id,
            "body": "Hello",
        },
    )
    dialog_id = created.json()["id"]
    recipient_token = create_token_pair(recipient)["access"]["token"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers = {"Authorization": f"Bearer {recipient_token}"}
        await client.get(f"/api/messages/{dialog_id}")
        response = await client.post(f"/api/messages/{dialog_id}", json={"body": "Yes"})
        assert response.status_code == 200
        assert response.json()["messages"][-1]["is_mine"] is True

    dialogs = await auth_ac.client.get("/api/messages")
    assert dialogs.json()[0]["unread_count"] == 1
    assert dialogs.json()[0]["latest_message"]["body"] == "Yes"


@pytest.mark.asyncio
async def test_cannot_message_a_non_matching_request(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipient = await factory.User()
    unrelated = await factory.Request(user=recipient, role=RequestRole.courier)
    own = await factory.Request(user=auth_ac.current_user, role=RequestRole.sender)
    monkeypatch.setattr("src.messages.service.notify_message_recipient", AsyncMock())

    response = await auth_ac.client.post(
        "/api/messages/from-match",
        json={
            "own_request_id": own.id,
            "matching_request_id": unrelated.id,
            "body": "Hello",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_message_notification_links_directly_to_dialog(
    factory: FactoryNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sender = await factory.User(tg_id=8001, name="Sender")
    recipient = await factory.User(tg_id=8002, name="Recipient")
    fake_bot = SimpleNamespace(
        send_message=AsyncMock(),
        session=SimpleNamespace(close=AsyncMock()),
    )
    monkeypatch.setattr("src.messages.service.Bot", lambda token: fake_bot)
    settings = SimpleNamespace(
        BOT_TOKEN=SecretStr("123:test"),
        WEBAPP_URL="https://example.com/webapp/",
    )

    await notify_message_recipient(recipient, sender, 42, "Hello there", settings)

    notification = fake_bot.send_message.await_args.kwargs
    assert notification["chat_id"] == recipient.tg_id
    assert notification["text"] == "Sender sent you a message:\n\nHello there"
    button = notification["reply_markup"].inline_keyboard[0][0]
    assert button.web_app.url == "https://example.com/webapp/?tab=messages&dialog=42"
    fake_bot.session.close.assert_awaited_once()
