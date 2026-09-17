from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination import Page

from src.auth.deps import get_current_user
from src.database import RequestStatus
from src.requests.schemas import RequestCreateSchema, RequestSchema, RequestStatusUpdateSchema
from src.requests.service import (
    create_user_request,
    get_user_requests,
    update_user_request_status,
)

requests_router = APIRouter(prefix="/api/requests", tags=["Requests"])


@requests_router.get("", response_model=Page[RequestSchema])
async def get_my_requests(
    status: RequestStatus | None = Query(None),
    language: str = Query("en", min_length=2, max_length=16),
    user=Depends(get_current_user),
):
    return await get_user_requests(user.id, status, language)


@requests_router.post(
    "",
    response_model=RequestSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    payload: RequestCreateSchema,
    user=Depends(get_current_user),
):
    return await create_user_request(user.id, payload)


@requests_router.patch("/{request_id}/status", response_model=RequestSchema)
async def update_request_status(
    request_id: int,
    payload: RequestStatusUpdateSchema,
    user=Depends(get_current_user),
):
    return await update_user_request_status(user.id, request_id, payload.status)
