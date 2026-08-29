from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from src.database import RequestStatus

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
async def test_city_search_matches_city_and_country(
    auth_ac: AuthenticatedClient,
    factory: FactoryNamespace,
) -> None:
    city = await factory.City(name="Jakarta", country__name="Indonesia")

    city_response = await auth_ac.client.get(
        "/api/city-search", params={"q": "Jakar"}
    )
    country_response = await auth_ac.client.get(
        "/api/city-search", params={"q": "Indones"}
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
