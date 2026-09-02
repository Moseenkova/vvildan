from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import (
    async_session_maker,
    City,
    Request as TravelRequest,
    RequestStatus,
)
from src.deps import get_current_user
from src.schemas import RequestCreateSchema, RequestSchema

requests_router = APIRouter(prefix="/api/requests", tags=["Requests"])


@requests_router.get("", response_model=Page[RequestSchema])
async def get_my_requests(
    status: RequestStatus | None = Query(None),
    user=Depends(get_current_user),
):
    departure_load = selectinload(TravelRequest.departure_cities).selectinload(
        City.country
    )
    arrival_load = selectinload(TravelRequest.arrival_cities).selectinload(City.country)
    async with async_session_maker() as session:
        query = (
            select(TravelRequest)
            .where(
                TravelRequest.user_id == user.id,
                *([TravelRequest.status == status] if status else []),
            )
            .options(departure_load, arrival_load)
            .order_by(TravelRequest.created_at.desc())
        )
        return await apaginate(session, query)


@requests_router.post(
    "",
    response_model=RequestSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    payload: RequestCreateSchema,
    user=Depends(get_current_user),
):
    city_ids = set(payload.departure_city_ids + payload.arrival_city_ids)
    async with async_session_maker() as session:
        cities = (
            await session.scalars(
                select(City)
                .where(City.id.in_(city_ids))
                .options(selectinload(City.country))
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
            user_id=user.id,
            role=payload.role,
            date_from=payload.date_from,
            date_to=payload.date_to,
            departure_cities=[cities_by_id[id] for id in payload.departure_city_ids],
            arrival_cities=[cities_by_id[id] for id in payload.arrival_city_ids],
            comment=payload.comment,
        )
        session.add(request)
        await session.commit()
        created_request = (
            await session.scalars(
                select(TravelRequest)
                .where(TravelRequest.id == request.id)
                .options(
                    selectinload(TravelRequest.departure_cities).selectinload(
                        City.country
                    ),
                    selectinload(TravelRequest.arrival_cities).selectinload(
                        City.country
                    ),
                )
            )
        ).one()
        return created_request
