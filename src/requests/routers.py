from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination import Page

from src.database import RequestStatus
from src.deps import get_current_user
from src.requests.service import create_user_request, get_user_requests
from src.requests.schemas import RequestCreateSchema, RequestSchema

requests_router = APIRouter(prefix="/api/requests", tags=["Requests"])


@requests_router.get("", response_model=Page[RequestSchema])
async def get_my_requests(
    status: RequestStatus | None = Query(None),
    user=Depends(get_current_user),
):
    return await get_user_requests(user.id, status)


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
