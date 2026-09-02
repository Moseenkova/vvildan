from typing import Any

from jose import JWTError, jwt
from sqlalchemy import delete, select

from src.auth.utils import create_token_pair
from src.config import Settings, get_settings
from src.database import async_session_maker, RefreshToken, User
from src.exceptions import (
    AuthFailedException,
    RefreshTokenRequiredException,
    TokenNotFoundException,
    UserNotFoundException,
)

cfg: Settings = get_settings()


def _get_user_id(payload: dict[str, object]) -> int:
    subject = payload.get(cfg.SUB)
    if not isinstance(subject, (str, int)) or isinstance(subject, bool):
        raise AuthFailedException

    try:
        return int(subject)
    except ValueError as exc:
        raise AuthFailedException from exc


async def get_user_by_id(user_id: int) -> User | None:
    async with async_session_maker() as session:
        return await session.scalar(select(User).where(User.id == user_id))


async def _get_user_by_telegram_id(telegram_id: int) -> User | None:
    async with async_session_maker() as session:
        return await session.scalar(select(User).where(User.tg_id == telegram_id))


async def _get_refresh_token(token_id: object) -> RefreshToken | None:
    async with async_session_maker() as session:
        return await session.scalar(
            select(RefreshToken).where(RefreshToken.token_id == token_id)
        )


async def _save_refresh_token(user_id: int, token: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        session.add(
            RefreshToken(
                user_id=user_id,
                token_id=token["jti"],
                expire=token["expire"],
            )
        )
        await session.commit()


async def _delete_refresh_tokens(*filters: object) -> None:
    async with async_session_maker() as session:
        await session.execute(delete(RefreshToken).where(*filters))
        await session.commit()


async def decode_access_token(token: str) -> dict[str, object]:
    try:
        return jwt.decode(token, cfg.SECRET_KEY, algorithms=[cfg.ALGORITHM])
    except JWTError as exc:
        raise TokenNotFoundException() from exc


async def authenticate_telegram_user(telegram_id: int) -> dict[str, Any]:
    user = await _get_user_by_telegram_id(telegram_id)
    if not user:
        raise UserNotFoundException

    token_pair = create_token_pair(user=user)
    await _save_refresh_token(user.id, token_pair["refresh"])
    return token_pair


async def rotate_refresh_token(refresh_token: str | None) -> dict[str, Any]:
    if not refresh_token:
        raise RefreshTokenRequiredException

    try:
        payload = jwt.decode(
            refresh_token,
            cfg.SECRET_KEY,
            algorithms=[cfg.ALGORITHM],
        )
    except JWTError as exc:
        raise AuthFailedException from exc

    token_id = payload.get(cfg.JTI)
    user_id = _get_user_id(payload)

    if not await _get_refresh_token(token_id):
        raise AuthFailedException

    user = await get_user_by_id(user_id)
    if not user:
        raise UserNotFoundException

    token_pair = create_token_pair(user=user)
    await _delete_refresh_tokens(RefreshToken.token_id == token_id)
    await _save_refresh_token(user.id, token_pair["refresh"])
    return token_pair


async def logout_user(access_token: str) -> None:
    try:
        payload = await decode_access_token(access_token)
        user_id = _get_user_id(payload)
        await _delete_refresh_tokens(RefreshToken.user_id == user_id)
    except Exception:
        pass
