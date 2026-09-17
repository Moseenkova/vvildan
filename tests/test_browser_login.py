import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from src.auth import telegram_login
from src.config import get_settings


@pytest.fixture
def signing_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private, {**jwk.construct(public, algorithm="RS256").to_dict(), "kid": "test-key"}


@pytest.fixture(autouse=True)
def telegram_config(monkeypatch, signing_key):
    monkeypatch.setattr(get_settings(), "TELEGRAM_LOGIN_CLIENT_ID", 123456)
    monkeypatch.setattr(Bot, "get_me", AsyncMock(return_value=SimpleNamespace(username="test_bot")))
    monkeypatch.setattr(
        telegram_login,
        "get_telegram_jwks",
        AsyncMock(return_value={"keys": [signing_key[1]]}),
    )


def signed_token(signing_key, user_id, expected_nonce, **overrides):
    now = int(time.time())
    claims = {
        "iss": telegram_login.ISSUER,
        "aud": "123456",
        "sub": "oidc-subject-is-not-the-telegram-user-id",
        "id": user_id,
        "iat": now,
        "exp": now + 300,
        "nonce": expected_nonce,
        **overrides,
    }
    claims = {key: value for key, value in claims.items() if value is not None}
    return jwt.encode(claims, signing_key[0], algorithm="RS256", headers={"kid": "test-key"})


async def login_nonce(client):
    response = await client.get("/api/auth/telegram/config")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["client_id"] == 123456
    return response.json()["nonce"]


@pytest.mark.asyncio
@pytest.mark.parametrize("id_type", [int, str])
async def test_browser_login_returns_usable_token_and_consumes_nonce(
    client, factory, signing_key, id_type
):
    user = await factory.User()
    token = signed_token(signing_key, id_type(user.tg_id), await login_nonce(client))
    response = await client.post("/api/auth/telegram", json={"id_token": token})
    assert response.status_code == 200
    assert get_settings().REFRESH_COOKIE_NAME in response.cookies
    requests = await client.get(
        "/api/requests", headers={"Authorization": f'Bearer {response.json()["access_token"]}'}
    )
    assert requests.status_code == 200
    repeat = await client.post("/api/auth/telegram", json={"id_token": token})
    assert repeat.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [
        {"exp": 1},
        {"exp": None},
        {"iat": 1},
        {"iat": int(time.time()) + 300},
        {"iss": "https://attacker.example"},
        {"aud": "other-bot"},
        {"aud": None},
        {"nonce": "another-browser"},
        {"nonce": None},
        {"id": None},
        {"id": True},
        {"id": -1},
        {"id": ""},
        {"id": "invalid"},
        {"id": "123.5"},
        {"id": "-1"},
        {"id": "0"},
        {"id": "１２３"},
        {"id": "9223372036854775808"},
        {"id": 123.5},
        {"sub": None},
    ],
)
async def test_browser_login_rejects_invalid_claims(client, factory, signing_key, override):
    user = await factory.User()
    nonce = await login_nonce(client)
    token = signed_token(signing_key, user.tg_id, nonce, **override)
    response = await client.post("/api/auth/telegram", json={"id_token": token})
    assert response.status_code == 401
    assert get_settings().REFRESH_COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_browser_login_rejects_wrong_signing_key(client, factory, signing_key, monkeypatch):
    user = await factory.User()
    token = signed_token(signing_key, user.tg_id, await login_nonce(client))
    monkeypatch.setattr(telegram_login, "get_telegram_jwks", AsyncMock(return_value={"keys": []}))
    response = await client.post("/api/auth/telegram", json={"id_token": token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_browser_login_rejects_wrong_algorithm(client):
    nonce = await login_nonce(client)
    token = jwt.encode({"nonce": nonce}, "attacker-key", algorithm="HS256")
    response = await client.post("/api/auth/telegram", json={"id_token": token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_browser_login_requires_matching_browser_session(client, signing_key):
    nonce = await login_nonce(client)
    client.cookies.clear()
    token = signed_token(signing_key, 999999, nonce)
    response = await client.post("/api/auth/telegram", json={"id_token": token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_browser_login_requires_registered_user(client, signing_key):
    token = signed_token(signing_key, 999999, await login_nonce(client))
    response = await client.post("/api/auth/telegram", json={"id_token": token})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_browser_login_requires_configuration(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "TELEGRAM_LOGIN_CLIENT_ID", None)
    response = await client.get("/api/auth/telegram/config")
    assert response.status_code == 503
