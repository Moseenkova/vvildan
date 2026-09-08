from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("end_date", [None, "omitted"])
async def test_open_sender_request(auth_ac, factory, end_date):
    city = await factory.City()
    payload = {
        "role": "sender",
        "dateFrom": "2026-09-10",
        "departureCityIds": [city.id],
        "arrivalCityIds": [city.id],
        "baggageComments": "Parcel",
    }
    if end_date is None:
        payload["dateTo"] = None
    response = await auth_ac.client.post("/api/requests", json=payload)
    assert response.status_code == 201
    assert response.json()["date_to"] is None
    rows = (await auth_ac.client.get("/api/requests")).json()
    assert rows["items"] == [response.json()]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,dates",
    [
        ("courier", {"dateFrom": "2026-09-10"}),
        ("courier", {"dateFrom": "2026-09-10", "dateTo": None}),
        ("courier", {"dateFrom": "2026-09-10", "dateTo": "2026-09-11"}),
        ("courier", {"dateTo": "2026-09-10"}),
        ("sender", {"dateTo": "2026-09-10"}),
        ("sender", {"dateFrom": "2026-09-10", "dateTo": "2026-09-09"}),
    ],
)
async def test_invalid_request_dates(auth_ac, factory, role, dates):
    city = await factory.City()
    response = await auth_ac.client.post(
        "/api/requests",
        json={
            "role": role,
            **dates,
            "departureCityIds": [city.id],
            "arrivalCityIds": [city.id],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("open_ended", [False, True])
async def test_open_requests_count_toward_limit(auth_ac, factory, open_ended):
    today = datetime.now(timezone.utc).date()
    city = await factory.City()
    for _ in range(5):
        await factory.Request(user=auth_ac.current_user, date_from=today, date_to=None)
    response = await auth_ac.client.post(
        "/api/requests",
        json={
            "role": "sender",
            "dateFrom": today.isoformat(),
            "dateTo": None if open_ended else today.isoformat(),
            "departureCityIds": [city.id],
            "arrivalCityIds": [city.id],
        },
    )
    assert response.status_code == 409
