from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from src.auth.schemas import TelegramLoginSchema
from src.auth.services import (
    authenticate_telegram_init_data,
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


@auth_router.post("/login")
async def login_user(payload: TelegramLoginSchema, response: Response):
    token_pair = await authenticate_telegram_init_data(payload.init_data)

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


@auth_router.post("/dev-login", include_in_schema=False)
async def dev_login_user(response: Response):
    if cfg.MODE == "PROD" or cfg.DEV_CHAT_ID is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    token_pair = await authenticate_telegram_user(cfg.DEV_CHAT_ID)

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
