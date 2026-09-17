import secrets
import time
from typing import Annotated

from aiogram import Bot
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from src.auth.deps import oauth2_scheme
from src.auth.schemas import TelegramBrowserLoginSchema, TelegramLoginSchema
from src.auth.services import (
    authenticate_telegram_init_data,
    authenticate_telegram_user,
    logout_user,
    rotate_refresh_token,
)
from src.auth.telegram_login import authenticate_telegram_id_token, reject_telegram_login
from src.config import Settings, get_settings

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


@auth_router.get("/telegram/config")
async def telegram_login_config(request: Request, response: Response):
    if cfg.TELEGRAM_LOGIN_CLIENT_ID is None:
        raise HTTPException(503, "Telegram browser login is not configured")
    async with Bot(token=cfg.BOT_TOKEN.get_secret_value()) as bot:
        user = await bot.get_me()
    nonce = secrets.token_urlsafe(32)
    request.session["telegram_login"] = {"nonce": nonce, "created_at": time.time()}
    response.headers["Cache-Control"] = "no-store"
    return {
        "bot_username": user.username,
        "client_id": cfg.TELEGRAM_LOGIN_CLIENT_ID,
        "nonce": nonce,
    }


@auth_router.post("/telegram")
async def telegram_browser_login(
    payload: TelegramBrowserLoginSchema, request: Request, response: Response
):
    pending = request.session.pop("telegram_login", None)
    if not pending:
        reject_telegram_login("missing_browser_session")
    if not 0 <= time.time() - pending["created_at"] <= cfg.TELEGRAM_AUTH_MAX_AGE_SECONDS:
        reject_telegram_login("expired_browser_session")
    token_pair = await authenticate_telegram_id_token(payload.id_token, pending["nonce"])
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=cfg.REFRESH_COOKIE_NAME,
        value=token_pair["refresh"]["token"],
        httponly=True,
        secure=cfg.MODE == "PROD",
        samesite="lax",
        max_age=cfg.REFRESH_TOKEN_EXPIRES_MINUTES * 60,
    )
    return {
        "access_token": token_pair["access"]["token"],
        "expire": token_pair["access"]["expire"],
    }
