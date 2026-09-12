from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select

from src.database import Match, RequestRole, User, async_session_maker
from src.matches.service import (
    get_user_matches,
    notify_match_users,
    notify_request_candidates,
)
from tests.conftest import AuthenticatedClient
from tests.factories import FactoryNamespace


@pytest.mark.asyncio
async def test_get_matches_returns_only_current_users_matches(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    courier = await factory.User(name="Matching Courier", username="courier")
    other_user = await factory.User()
    departure = await factory.City(name="Jakarta")
    arrival = await factory.City(name="Singapore")
    sender_request = await factory.Request(
        user=auth_ac.current_user,
        role=RequestRole.sender,
        departure_cities=[departure],
        arrival_cities=[arrival],
        comment="Small parcel",
    )
    courier_request = await factory.Request(
        user=courier,
        role=RequestRole.courier,
        date_from=date(2026, 9, 1),
        date_to=date(2026, 9, 1),
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    match = await factory.Match(
        sender_request=sender_request,
        courier_request=courier_request,
    )
    unrelated_sender = await factory.Request(user=other_user, role=RequestRole.sender)
    unrelated_courier = await factory.Request(role=RequestRole.courier)
    await factory.Match(
        sender_request=unrelated_sender,
        courier_request=unrelated_courier,
    )

    response = await auth_ac.client.get("/api/matches")

    assert response.status_code == 200
    assert len(response.json()) == 1
    body = response.json()[0]
    assert body["id"] == match.id
    assert body["is_new"] is True
    assert body["is_candidate"] is False
    assert body["own_request"]["id"] == sender_request.id
    assert body["matching_request"]["id"] == courier_request.id
    assert body["matching_user"] == {"name": "Matching Courier", "username": "courier"}


@pytest.mark.asyncio
async def test_mark_matches_seen_updates_only_current_users_side(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    sender_request = await factory.Request(user=auth_ac.current_user, role=RequestRole.sender)
    courier_request = await factory.Request(role=RequestRole.courier)
    match = await factory.Match(
        sender_request=sender_request,
        courier_request=courier_request,
    )

    response = await auth_ac.client.post("/api/matches/seen")

    assert response.status_code == 204
    async with async_session_maker() as session:
        stored = (await session.scalars(select(Match).where(Match.id == match.id))).one()
        assert stored.sender_seen_at is not None
        assert stored.courier_seen_at is None
        stored_user = await session.get(User, auth_ac.current_user.id)
        assert stored_user.matches_seen_at is not None

    matches_response = await auth_ac.client.get("/api/matches")
    assert matches_response.json()[0]["is_new"] is False


@pytest.mark.asyncio
async def test_matches_require_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/matches")).status_code == 401
    assert (await client.post("/api/matches/seen")).status_code == 401


@pytest.mark.asyncio
async def test_get_matches_includes_compatible_candidate_requests(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    departure = await factory.City(name="Moscow")
    arrival = await factory.City(name="Istanbul")
    other_arrival = await factory.City(name="Paris")
    sender_request = await factory.Request(
        user=auth_ac.current_user,
        role=RequestRole.sender,
        date_from=date(2026, 9, 12),
        date_to=None,
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    courier = await factory.User(name="Candidate Courier", username="candidate")
    candidate_request = await factory.Request(
        user=courier,
        role=RequestRole.courier,
        date_from=date(2026, 9, 13),
        date_to=date(2026, 9, 13),
        departure_cities=[departure],
        arrival_cities=[arrival],
        comment="Electronics only",
    )
    await factory.Request(
        role=RequestRole.courier,
        date_from=date(2026, 9, 11),
        date_to=date(2026, 9, 11),
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    await factory.Request(
        role=RequestRole.courier,
        date_from=date(2026, 9, 13),
        date_to=date(2026, 9, 13),
        departure_cities=[departure],
        arrival_cities=[other_arrival],
    )

    response = await auth_ac.client.get("/api/matches")

    assert response.status_code == 200
    assert len(response.json()) == 1
    body = response.json()[0]
    assert body["id"] == candidate_request.id
    assert body["is_candidate"] is True
    assert body["is_new"] is True
    assert body["own_request"]["id"] == sender_request.id
    assert body["matching_user"]["name"] == "Candidate Courier"

    assert (await auth_ac.client.post("/api/matches/seen")).status_code == 204
    assert (await auth_ac.client.get("/api/matches")).json()[0]["is_new"] is False


@pytest.mark.asyncio
async def test_courier_sees_compatible_sender_candidate(
    factory: FactoryNamespace,
) -> None:
    departure = await factory.City(name="Moscow")
    arrival = await factory.City(name="Istanbul")
    sender = await factory.User(name="Candidate Sender")
    sender_request = await factory.Request(
        user=sender,
        role=RequestRole.sender,
        date_from=date(2026, 9, 12),
        date_to=None,
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    courier = await factory.User(name="Courier")
    courier_request = await factory.Request(
        user=courier,
        role=RequestRole.courier,
        date_from=date(2026, 9, 13),
        date_to=date(2026, 9, 13),
        departure_cities=[departure],
        arrival_cities=[arrival],
    )

    matches = await get_user_matches(courier.id)

    assert len(matches) == 1
    assert matches[0].is_candidate is True
    assert matches[0].own_request.id == courier_request.id
    assert matches[0].matching_request.id == sender_request.id


@pytest.mark.asyncio
async def test_notify_match_users_sends_details_and_webapp_button(
    factory: FactoryNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sender = await factory.User(tg_id=1001, name="Sender")
    courier = await factory.User(tg_id=1002, name="Courier")
    departure = await factory.City(name="Jakarta")
    arrival = await factory.City(name="Singapore")
    sender_request = await factory.Request(
        user=sender,
        role=RequestRole.sender,
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    courier_request = await factory.Request(
        user=courier,
        role=RequestRole.courier,
        date_from=date(2026, 9, 1),
        date_to=date(2026, 9, 1),
        departure_cities=[departure],
        arrival_cities=[arrival],
        comment="Documents",
    )
    match = await factory.Match(
        sender_request=sender_request,
        courier_request=courier_request,
    )

    fake_bot = SimpleNamespace(
        send_message=AsyncMock(),
        session=SimpleNamespace(close=AsyncMock()),
    )
    monkeypatch.setattr("src.matches.service.Bot", lambda token: fake_bot)
    settings = SimpleNamespace(
        BOT_TOKEN=SecretStr("123:test"),
        BASE_URL="https://example.com",
    )

    await notify_match_users(match.id, settings)

    assert fake_bot.send_message.await_count == 2
    sender_message = fake_bot.send_message.await_args_list[0].kwargs
    assert sender_message["chat_id"] == sender.tg_id
    assert "Courier" in sender_message["text"]
    assert "Jakarta → Singapore" in sender_message["text"]
    assert "Documents" in sender_message["text"]
    button = sender_message["reply_markup"].inline_keyboard[0][0]
    assert button.web_app.url == "https://example.com/webapp/?tab=matches"
    fake_bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_request_candidates_sends_new_request_and_matches_link(
    factory: FactoryNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sender = await factory.User(tg_id=2001, name="Sender")
    courier = await factory.User(tg_id=2002, name="New Courier")
    departure = await factory.City(name="Moscow")
    arrival = await factory.City(name="Istanbul")
    sender_request = await factory.Request(
        user=sender,
        role=RequestRole.sender,
        date_from=date(2026, 9, 12),
        date_to=None,
        departure_cities=[departure],
        arrival_cities=[arrival],
    )
    courier_request = await factory.Request(
        user=courier,
        role=RequestRole.courier,
        date_from=date(2026, 9, 13),
        date_to=date(2026, 9, 13),
        departure_cities=[departure],
        arrival_cities=[arrival],
        comment="Electronics only",
    )
    fake_bot = SimpleNamespace(
        send_message=AsyncMock(),
        session=SimpleNamespace(close=AsyncMock()),
    )
    monkeypatch.setattr("src.matches.service.Bot", lambda token: fake_bot)
    settings = SimpleNamespace(
        BOT_TOKEN=SecretStr("123:test"),
        BASE_URL="https://example.com",
    )

    await notify_request_candidates(courier_request.id, settings)

    fake_bot.send_message.assert_awaited_once()
    notification = fake_bot.send_message.await_args.kwargs
    assert notification["chat_id"] == sender.tg_id
    assert f"#{sender_request.id}" in notification["text"]
    assert "New Courier" in notification["text"]
    assert "Moscow → Istanbul" in notification["text"]
    assert "Electronics only" in notification["text"]
    button = notification["reply_markup"].inline_keyboard[0][0]
    assert button.web_app.url == "https://example.com/webapp/?tab=matches"
    fake_bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_creating_request_triggers_candidate_notifications(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    departure = await factory.City(name="Moscow")
    arrival = await factory.City(name="Istanbul")
    notify = AsyncMock()
    monkeypatch.setattr("src.matches.service.notify_request_candidates", notify)

    response = await auth_ac.client.post(
        "/api/requests",
        json={
            "role": "courier",
            "dateFrom": "2026-09-13",
            "dateTo": "2026-09-13",
            "departureCityIds": [departure.id],
            "arrivalCityIds": [arrival.id],
            "baggageComments": "Electronics only",
        },
    )

    assert response.status_code == 201
    notify.assert_awaited_once_with(response.json()["id"])
