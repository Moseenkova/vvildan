from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.database import Request as TravelRequest
from src.database import RequestStatus, async_session_maker


@pytest.mark.asyncio
async def test_user_can_cancel_and_reactivate_future_request(auth_ac, factory):
    today = datetime.now(timezone.utc).date()
    request = await factory.Request(
        user=auth_ac.current_user,
        date_from=today,
        date_to=today + timedelta(days=1),
    )

    cancel = await auth_ac.client.patch(
        f"/api/requests/{request.id}/status",
        json={"status": "cancelled"},
    )

    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert cancel.json()["can_cancel"] is False
    assert cancel.json()["can_reactivate"] is True

    reactivate = await auth_ac.client.patch(
        f"/api/requests/{request.id}/status",
        json={"status": "active"},
    )

    assert reactivate.status_code == 200
    assert reactivate.json()["status"] == "active"
    assert reactivate.json()["can_cancel"] is True
    assert reactivate.json()["can_reactivate"] is False

    async with async_session_maker() as session:
        saved = await session.get(TravelRequest, request.id)
        assert saved.status == RequestStatus.active


@pytest.mark.asyncio
async def test_open_ended_request_can_be_cancelled_and_reactivated(auth_ac, factory):
    today = datetime.now(timezone.utc).date()
    request = await factory.Request(
        user=auth_ac.current_user,
        date_from=today - timedelta(days=30),
        date_to=None,
    )

    cancel = await auth_ac.client.patch(
        f"/api/requests/{request.id}/status", json={"status": "cancelled"}
    )
    reactivate = await auth_ac.client.patch(
        f"/api/requests/{request.id}/status", json={"status": "active"}
    )

    assert cancel.status_code == 200
    assert reactivate.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("initial_status", "new_status"),
    [
        (RequestStatus.active, "cancelled"),
        (RequestStatus.cancelled, "active"),
    ],
)
async def test_passed_request_cannot_change_status(auth_ac, factory, initial_status, new_status):
    today = datetime.now(timezone.utc).date()
    request = await factory.Request(
        user=auth_ac.current_user,
        status=initial_status,
        date_from=today - timedelta(days=2),
        date_to=today - timedelta(days=1),
    )

    response = await auth_ac.client.patch(
        f"/api/requests/{request.id}/status", json={"status": new_status}
    )

    assert response.status_code == 409
    assert "closing date has passed" in response.json()["detail"]

    listed = (await auth_ac.client.get("/api/requests")).json()["items"][0]
    assert listed["can_cancel"] is False
    assert listed["can_reactivate"] is False


@pytest.mark.asyncio
async def test_completed_and_expired_requests_offer_no_status_action(auth_ac, factory):
    today = datetime.now(timezone.utc).date()
    for status in (RequestStatus.completed, RequestStatus.expired):
        await factory.Request(
            user=auth_ac.current_user,
            status=status,
            date_from=today,
            date_to=today + timedelta(days=1),
        )

    items = (await auth_ac.client.get("/api/requests")).json()["items"]

    assert all(item["can_cancel"] is False for item in items)
    assert all(item["can_reactivate"] is False for item in items)


@pytest.mark.asyncio
async def test_user_cannot_change_another_users_request(auth_ac, factory):
    today = datetime.now(timezone.utc).date()
    request = await factory.Request(date_from=today, date_to=today + timedelta(days=1))

    response = await auth_ac.client.patch(
        f"/api/requests/{request.id}/status", json={"status": "cancelled"}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reactivation_respects_active_request_limit(auth_ac, factory):
    today = datetime.now(timezone.utc).date()
    for _ in range(5):
        await factory.Request(
            user=auth_ac.current_user,
            date_from=today,
            date_to=today + timedelta(days=1),
        )
    cancelled = await factory.Request(
        user=auth_ac.current_user,
        status=RequestStatus.cancelled,
        date_from=today,
        date_to=today + timedelta(days=1),
    )

    response = await auth_ac.client.patch(
        f"/api/requests/{cancelled.id}/status", json={"status": "active"}
    )

    assert response.status_code == 409
    assert "at most 5 active requests" in response.json()["detail"]
    async with async_session_maker() as session:
        status = await session.scalar(
            select(TravelRequest.status).where(TravelRequest.id == cancelled.id)
        )
        assert status == RequestStatus.cancelled
