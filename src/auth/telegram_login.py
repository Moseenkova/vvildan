"""Verify current Telegram Login SDK ID tokens independently of Mini App initData."""

import asyncio
import hmac
import json
import logging
import time
from typing import Any, NoReturn
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import HTTPException
from jose import JWTError, jwt

from src.auth.services import authenticate_telegram_user
from src.config import get_settings

logger = logging.getLogger(__name__)


def reject_telegram_login(reason: str) -> NoReturn:
    logger.warning("Telegram browser login rejected: %s", reason)
    raise HTTPException(401, f"Telegram login verification failed ({reason}). Please try again.")


ISSUER = "https://oauth.telegram.org"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
_jwks_cache: dict[str, Any] = {}
_jwks_expires = 0.0


def _download_jwks() -> dict[str, Any]:
    with urlopen(JWKS_URL, timeout=10) as response:
        return json.load(response)


async def get_telegram_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_expires
    if time.monotonic() >= _jwks_expires:
        try:
            keys = await asyncio.to_thread(_download_jwks)
            if not isinstance(keys, dict) or not isinstance(keys.get("keys"), list):
                raise ValueError("Invalid Telegram keys")
        except (URLError, TimeoutError, ValueError) as exc:
            raise HTTPException(503, "Telegram login is temporarily unavailable") from exc
        _jwks_cache = keys
        _jwks_expires = time.monotonic() + 300
    return _jwks_cache


async def authenticate_telegram_id_token(id_token: str, nonce: str) -> dict[str, Any]:
    cfg = get_settings()
    if cfg.TELEGRAM_LOGIN_CLIENT_ID is None:
        raise HTTPException(503, "Telegram browser login is not configured")
    try:
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") != "RS256":
            reject_telegram_login("unsupported_signing_algorithm")
        keys = await get_telegram_jwks()
        claims = jwt.decode(
            id_token,
            keys,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=str(cfg.TELEGRAM_LOGIN_CLIENT_ID),
            options={
                "require_exp": True,
                "require_iat": True,
                "require_aud": True,
                "require_iss": True,
                "require_sub": True,
            },
        )
        signed_nonce = claims.get("nonce")
        if not isinstance(signed_nonce, str) or not hmac.compare_digest(
            signed_nonce.encode(), nonce.encode()
        ):
            reject_telegram_login("nonce_mismatch")
        issued_at = claims["iat"]
        if not isinstance(issued_at, int) or isinstance(issued_at, bool):
            reject_telegram_login("invalid_issue_time")
        if not -30 <= time.time() - issued_at <= cfg.TELEGRAM_AUTH_MAX_AGE_SECONDS:
            reject_telegram_login("expired_id_token")
        # The OIDC subject is not the Bot API user ID. Request profile scope and use id.
        telegram_id = claims.get("id")
        # Telegram can encode the signed profile ID as a JSON number or decimal string.
        if isinstance(telegram_id, str):
            if not (telegram_id.isascii() and telegram_id.isdecimal() and len(telegram_id) <= 19):
                reject_telegram_login("invalid_profile_id")
            telegram_id = int(telegram_id)
        if (
            not isinstance(telegram_id, int)
            or isinstance(telegram_id, bool)
            or not 0 < telegram_id < 2**63
        ):
            logger.warning(
                "Telegram profile ID type: %s; claim names: %s",
                type(telegram_id).__name__,
                sorted(claims),
            )
            reject_telegram_login("invalid_profile_id")
    except (JWTError, ValueError, TypeError, KeyError) as exc:
        logger.warning("Telegram ID token validation: %s: %s", type(exc).__name__, str(exc))
        reject_telegram_login("invalid_id_token")
    locale = claims.get("locale")
    return await authenticate_telegram_user(
        telegram_id,
        locale if isinstance(locale, str) else None,
    )
