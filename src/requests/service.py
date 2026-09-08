from datetime import datetime, timezone

from fastapi import HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.config import Settings, get_settings
from src.database import City, RequestStatus, User, async_session_maker
from src.database import Request as TravelRequest
from src.requests.schemas import RequestCreateSchema

cfg: Settings = get_settings()


def _city_relationships():
    return (
        selectinload(TravelRequest.departure_cities).selectinload(City.country),
        selectinload(TravelRequest.arrival_cities).selectinload(City.country),
    )


async def get_user_requests(
    user_id: int,
    request_status: RequestStatus | None = None,
) -> Page[TravelRequest]:
    async with async_session_maker() as session:
        query = (
            select(TravelRequest)
            .where(
                TravelRequest.user_id == user_id,
                *([TravelRequest.status == request_status] if request_status else []),
            )
            .options(*_city_relationships())
            .order_by(TravelRequest.created_at.desc())
        )
        return await apaginate(session, query)


async def create_user_request(
    user_id: int,
    payload: RequestCreateSchema,
) -> TravelRequest:
    city_ids = set(payload.departure_city_ids + payload.arrival_city_ids)

    async with async_session_maker() as session:
        # Serialize creation for this user so concurrent submissions cannot exceed the cap.
        await session.execute(select(User.id).where(User.id == user_id).with_for_update())
        today = datetime.now(timezone.utc).date()
        if payload.date_to >= today:
            active_count = await session.scalar(
                select(func.count())
                .select_from(TravelRequest)
                .where(
                    TravelRequest.user_id == user_id,
                    TravelRequest.status == RequestStatus.active,
                    TravelRequest.date_to >= today,
                )
            )
            if active_count >= cfg.MAX_ACTIVE_REQUESTS_PER_USER:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "You can have at most 5 active requests " "with an end date today or later."
                    ),
                )

        cities = (
            await session.scalars(
                select(City).where(City.id.in_(city_ids)).options(selectinload(City.country))
            )
        ).all()
        cities_by_id = {city.id: city for city in cities}
        missing_city_ids = sorted(city_ids - cities_by_id.keys())
        if missing_city_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"missing_city_ids": missing_city_ids},
            )

        request = TravelRequest(
            user_id=user_id,
            role=payload.role,
            date_from=payload.date_from,
            date_to=payload.date_to,
            departure_cities=[cities_by_id[id] for id in payload.departure_city_ids],
            arrival_cities=[cities_by_id[id] for id in payload.arrival_city_ids],
            comment=payload.comment,
        )
        session.add(request)
        await session.commit()

        return (
            await session.scalars(
                select(TravelRequest)
                .where(TravelRequest.id == request.id)
                .options(*_city_relationships())
            )
        ).one()
