from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from src.auth.services import (
    authenticate_telegram_user,
    logout_user,
    rotate_refresh_token,
)
from src.config import Settings, get_settings
from src.deps import oauth2_scheme

cfg: Settings = get_settings()

auth_router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"],
)


class TelegramLoginSchema(BaseModel):
    tg_id: int


@auth_router.post("/login")
async def login_user(payload: TelegramLoginSchema, response: Response):
    token_pair = await authenticate_telegram_user(payload.tg_id)

    response.set_cookie(
        key=cfg.REFRESH_COOKIE_NAME,
        value=token_pair["refresh"]["token"],
        httponly=True,
        max_age=cfg.REFRESH_TOKEN_EXPIRES_MINUTES * 60,
    )
    return {
        "access_token": token_pair["access"]["token"],
        "expire": token_pair["access"]["expire"],
    }


@auth_router.post("/refresh")
async def refresh(refresh: Annotated[str | None, Cookie()] = None):
    token_pair = await rotate_refresh_token(refresh)
    return {
        "access_token": token_pair["access"]["token"],
        "expire": token_pair["access"]["expire"],
    }


@auth_router.post("/logout")
async def logout(
    response: Response,
    token: Annotated[str, Depends(oauth2_scheme)],
):
    await logout_user(token)
    response.delete_cookie(cfg.REFRESH_COOKIE_NAME)
    return {"msg": "Successfully logout"}
