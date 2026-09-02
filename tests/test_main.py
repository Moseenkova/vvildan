from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from sqlalchemy import select

from src.database import Request as TravelRequest, RequestRole, RequestStatus, async_session_maker

from tests.conftest import AuthenticatedClient
from tests.factories import FactoryNamespace


@pytest.mark.asyncio
async def test_get_my_requests_returns_real_paginated_rows(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    user = auth_ac.current_user
    other_user = await factory.User()
    city = await factory.City()
    now = datetime(2026, 8, 22, 12, 0)

    oldest = await factory.Request(
        user=user,
        departure_cities=[city],
        arrival_cities=[city],
        created_at=now - timedelta(days=2),
    )
    middle = await factory.Request(
        user=user,
        departure_cities=[city],
        arrival_cities=[city],
        created_at=now - timedelta(days=1),
    )
    newest = await factory.Request(
        user=user,
        departure_cities=[city],
        arrival_cities=[city],
        created_at=now,
    )
    await factory.Request(
        user=other_user,
        departure_cities=[city],
        arrival_cities=[city],
        created_at=now + timedelta(days=1),
    )

    first_page = await auth_ac.client.get(
        "/api/requests",
        params={"page": 1, "size": 2},
    )

    assert first_page.status_code == 200
    body = first_page.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["pages"] == 2
    assert [item["id"] for item in body["items"]] == [newest.id, middle.id]
    assert body["items"][0]["departure_cities"] == [
        {
            "id": city.id,
            "name": city.name,
            "country_name": city.country.name,
        }
    ]

    second_page = await auth_ac.client.get(
        "/api/requests",
        params={"page": 2, "size": 2},
    )

    assert second_page.status_code == 200
    assert [item["id"] for item in second_page.json()["items"]] == [oldest.id]


@pytest.mark.asyncio
async def test_get_my_requests_filters_real_rows_by_status(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    user = auth_ac.current_user
    city = await factory.City()
    now = datetime(2026, 8, 22, 12, 0)
    active = await factory.Request(
        user=user,
        departure_cities=[city],
        arrival_cities=[city],
        status=RequestStatus.active,
        created_at=now,
    )
    completed = await factory.Request(
        user=user,
        departure_cities=[city],
        arrival_cities=[city],
        status=RequestStatus.completed,
        created_at=now + timedelta(minutes=1),
    )

    response = await auth_ac.client.get(
        "/api/requests",
        params={"status": "completed", "page": 1, "size": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [completed.id]
    assert active.id not in [item["id"] for item in body["items"]]


@pytest.mark.asyncio
async def test_get_my_requests_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/requests")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_sender_request(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    departure = await factory.City(name="Jakarta")
    arrival = await factory.City(name="Singapore")

    response = await auth_ac.client.post(
        "/api/requests",
        json={
            "role": "sender",
            "dateFrom": "2026-09-10",
            "dateTo": "2026-09-12",
            "departureCityIds": [departure.id],
            "arrivalCityIds": [arrival.id],
            "baggageComments": "One small parcel",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "sender"
    assert body["date_from"] == "2026-09-10"
    assert body["date_to"] == "2026-09-12"
    assert [city["id"] for city in body["departure_cities"]] == [departure.id]
    assert [city["id"] for city in body["arrival_cities"]] == [arrival.id]
    assert body["comment"] == "One small parcel"
    assert body["status"] == "active"

    async with async_session_maker() as session:
        created = (await session.scalars(select(TravelRequest))).one()
        assert created.user_id == auth_ac.current_user.id
        assert created.role == RequestRole.sender
        assert created.date_from.isoformat() == "2026-09-10"
        assert created.date_to.isoformat() == "2026-09-12"


@pytest.mark.asyncio
async def test_create_courier_request(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    departure = await factory.City()
    arrival = await factory.City()

    response = await auth_ac.client.post(
        "/api/requests",
        json={
            "role": "courier",
            "dateFrom": "2026-09-10",
            "dateTo": "2026-09-10",
            "departureCityIds": [departure.id],
            "arrivalCityIds": [arrival.id],
            "baggageComments": '<script>alert("xss")</script>',
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "courier"
    assert body["date_from"] == "2026-09-10"
    assert body["date_to"] == "2026-09-10"
    assert [city["id"] for city in body["departure_cities"]] == [departure.id]
    assert [city["id"] for city in body["arrival_cities"]] == [arrival.id]
    assert body["comment"] == (
        "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
    )
    assert body["status"] == "active"

    async with async_session_maker() as session:
        created = (await session.scalars(select(TravelRequest))).one()
        assert created.user_id == auth_ac.current_user.id
        assert created.role == RequestRole.courier
        assert created.date_from.isoformat() == "2026-09-10"
        assert created.date_to.isoformat() == "2026-09-10"


@pytest.mark.asyncio
async def test_create_request_then_get_it(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    departure = await factory.City(name="Jakarta")
    arrival = await factory.City(name="Singapore")

    create_response = await auth_ac.client.post(
        "/api/requests",
        json={
            "role": "sender",
            "dateFrom": "2026-09-10",
            "dateTo": "2026-09-12",
            "departureCityIds": [departure.id],
            "arrivalCityIds": [arrival.id],
            "baggageComments": "One small parcel",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()

    get_response = await auth_ac.client.get("/api/requests")

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["total"] == 1
    assert body["items"] == [created]


@pytest.mark.asyncio
async def test_city_search_matches_city_and_country(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    city = await factory.City(name="Jakarta", country__name="Indonesia")

    city_response = await auth_ac.client.get(
        "/api/search", params={"q": "Jakar"}
    )
    country_response = await auth_ac.client.get(
        "/api/search", params={"q": "Indones"}
    )

    expected = {
        "id": city.id,
        "name": city.name,
        "country_id": city.country.id,
        "country_name": city.country.name,
    }
    assert city_response.status_code == 200
    assert city_response.json() == [expected]
    assert country_response.status_code == 200
    assert country_response.json() == [expected]
