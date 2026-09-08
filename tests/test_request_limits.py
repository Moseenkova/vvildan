from datetime import datetime, timedelta, timezone

import pytest

from src.database import RequestRole, RequestStatus


@pytest.mark.asyncio
async def test_active_request_limit_is_shared_across_roles(auth_ac, factory):
    today = datetime.now(timezone.utc).date()
    city = await factory.City()
    for role in [RequestRole.sender, RequestRole.courier] * 2:
        await factory.Request(user=auth_ac.current_user, role=role, date_from=today, date_to=today)

    # Neither historical/inactive requests nor another user's requests use this quota.
    await factory.Request(
        user=auth_ac.current_user,
        date_from=today - timedelta(days=2),
        date_to=today - timedelta(days=1),
    )
    for status in [RequestStatus.cancelled, RequestStatus.completed, RequestStatus.expired]:
        await factory.Request(
            user=auth_ac.current_user, status=status, date_from=today, date_to=today
        )
    await factory.Request(date_from=today, date_to=today)

    payload = {
        "role": "sender",
        "dateFrom": today.isoformat(),
        "dateTo": (today + timedelta(days=1)).isoformat(),
        "departureCityIds": [city.id],
        "arrivalCityIds": [city.id],
        "baggageComments": "Parcel",
    }
    fifth = await auth_ac.client.post("/api/requests", json=payload)
    assert fifth.status_code == 201

    payload["role"] = "courier"
    sixth = await auth_ac.client.post("/api/requests", json=payload)
    assert sixth.status_code == 409
    assert "at most 5 active requests" in sixth.json()["detail"]

    rows = (await auth_ac.client.get("/api/requests")).json()
    assert rows["total"] == 9
