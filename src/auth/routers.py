from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel

from src.auth.utils import create_token_pair
from src.config import Settings, get_settings
from src.dao import UserDAO, RefreshTokenDAO
from src.database import RefreshToken, User
from src.deps import oauth2_scheme, decode_access_token
from src.exceptions import (
    RefreshTokenRequiredException,
    UserNotFoundException,
    AuthFailedException,
)

cfg: Settings = get_settings()

auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


def _get_user_id(payload: dict[str, object]) -> int:
    subject = payload.get(cfg.SUB)
    if not isinstance(subject, (str, int)) or isinstance(subject, bool):
        raise AuthFailedException

    try:
        return int(subject)
    except ValueError as exc:
        raise AuthFailedException from exc


class TelegramLoginSchema(BaseModel):
    tg_id: int

@auth_router.post("/login")
async def login_user(payload: TelegramLoginSchema, response: Response):
    user = await UserDAO.get_by_tg_id(payload.tg_id)
    if not user:
        raise UserNotFoundException

    token_pair = create_token_pair(user=user)

    await RefreshTokenDAO.create(
        data={
            "user_id": user.id,
            "token_id": token_pair["refresh"]["jti"],
            "expire": token_pair["refresh"]["expire"],
        }
    )

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
    if not refresh:
        raise RefreshTokenRequiredException
    
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(refresh, cfg.SECRET_KEY, algorithms=[cfg.ALGORITHM])
    except JWTError:
        raise AuthFailedException
        
    token_id = payload.get(cfg.JTI)
    user_id = _get_user_id(payload)
    
    token_in_db = await RefreshTokenDAO.find_one_or_none(RefreshToken.token_id == token_id)
    if not token_in_db:
        raise AuthFailedException
        
    user = await UserDAO.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException
        
    token_pair = create_token_pair(user=user)
    
    # Delete old refresh token, save new one
    await RefreshTokenDAO.delete(RefreshToken.token_id == token_id)
    await RefreshTokenDAO.create(
        data={
            "user_id": user.id,
            "token_id": token_pair["refresh"]["jti"],
            "expire": token_pair["refresh"]["expire"],
        }
    )
    
    return {
        "access_token": token_pair["access"]["token"],
        "expire": token_pair["access"]["expire"],
    }


@auth_router.post("/logout")
async def logout(
    response: Response,
    token: Annotated[str, Depends(oauth2_scheme)],
):
    try:
        payload = await decode_access_token(token=token)
        # We delete ALL refresh tokens for simplicity, or we could pass the refresh token specifically.
        # It's better to delete all refresh tokens to effectively log out from all devices, or just rely on cookie deletion.
        user_id = _get_user_id(payload)
        await RefreshTokenDAO.delete(RefreshToken.user_id == user_id)
    except:
        pass

    response.delete_cookie(cfg.REFRESH_COOKIE_NAME)
    return {"msg": "Successfully logout"}
