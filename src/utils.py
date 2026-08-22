import uuid
import sys
from datetime import timedelta, datetime, timezone

from jose import jwt
from fastapi import Response

from src.auth.schemas import JwtTokenSchema, TokenPair

from src.config import Settings, get_settings
from src.users.models import User
import bcrypt

cfg: Settings = get_settings()


def verify_password(plain_password, hashed_password) -> bool:
    plain_password_byte = plain_password.encode("utf-8")
    hashed_password_byte = hashed_password.encode("utf-8")
    return bcrypt.checkpw(
        password=plain_password_byte, hashed_password=hashed_password_byte
    )


def _get_utc_now():
    if sys.version_info >= (3, 2):
        # For Python 3.2 and later
        current_utc_time = datetime.now(timezone.utc)
    else:
        # For older versions of Python
        current_utc_time = datetime.utcnow()
    return current_utc_time


def create_jwt_token(payload: dict, kind: str) -> JwtTokenSchema:
    if kind == "access":
        minutes = cfg.ACCESS_TOKEN_EXPIRE_MINUTES
    elif kind == "refresh":
        minutes = cfg.REFRESH_TOKEN_EXPIRES_MINUTES
    else:
        raise

    expire = _get_utc_now() + timedelta(minutes=minutes)

    payload[cfg.EXP] = expire

    token = JwtTokenSchema(
        token=jwt.encode(payload, cfg.SECRET_KEY, algorithm=cfg.ALGORITHM),
        payload=payload,
        expire=expire,
    )

    return token


def create_token_pair(user: User) -> TokenPair:
    payload = {
        cfg.SUB: str(user.id),
        cfg.JTI: str(uuid.uuid4()),
        cfg.IAT: _get_utc_now(),
    }

    return TokenPair(
        access=create_jwt_token(payload={**payload}, kind="access"),
        refresh=create_jwt_token(payload={**payload}, kind="refresh"),
    )


def add_refresh_token_cookie(response: Response, token: str):
    exp = _get_utc_now() + timedelta(minutes=cfg.REFRESH_TOKEN_EXPIRES_MINUTES)

    response.set_cookie(
        key=cfg.REFRESH_COOKIE_NAME,
        value=token,
        expires=exp,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=cfg.REFRESH_TOKEN_EXPIRES_MINUTES * 60,
        path="/",
    )


async def get_topic_id_by_customer_chat_id(customer_chat_id: int) -> int | None:
    with Session() as session:
        return (
            session.query(CustomerTgTopic.c.topic_id)
            .filter(CustomerTgTopic.c.customer_chat_id == customer_chat_id)
            .scalar()
        )


async def create_customer_tg_topic(customer_chat_id: int, topic_id: int) -> int:
    with Session.begin() as session:
        session.execute(
            CustomerTgTopic.insert().values(
                customer_chat_id=customer_chat_id,
                topic_id=topic_id,
            )
        )

    return topic_id


async def get_customer_chat_id_by_topic_id(topic_id: int) -> int | None:
    with Session() as session:
        return (
            session.query(CustomerTgTopic.c.customer_chat_id)
            .filter(CustomerTgTopic.c.topic_id == topic_id)
            .scalar()
        )
