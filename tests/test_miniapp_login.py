import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from sqlalchemy import select

from src.config import get_settings
from src.database import User, async_session_maker


def signed_init_data(user_id, age=0, language_code=None):
    telegram_user = {"id": user_id, "first_name": "Telegram user"}
    if language_code:
        telegram_user["language_code"] = language_code
    data = {
        "auth_date": str(int(time.time()) - age),
        "query_id": "mini-app-launch",
        "user": json.dumps(telegram_user),
    }
    secret = hmac.new(
        b"WebAppData", get_settings().BOT_TOKEN.get_secret_value().encode(), hashlib.sha256
    ).digest()
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@pytest.mark.asyncio
async def test_miniapp_login_needs_no_browser_login_configuration(client, factory, monkeypatch):
    monkeypatch.setattr(get_settings(), "TELEGRAM_LOGIN_CLIENT_ID", None)
    user = await factory.User()
    response = await client.post(
        "/api/auth/login", json={"init_data": signed_init_data(user.tg_id)}
    )
    assert response.status_code == 200
    requests = await client.get(
        "/api/requests", headers={"Authorization": f'Bearer {response.json()["access_token"]}'}
    )
    assert requests.status_code == 200


@pytest.mark.asyncio
async def test_miniapp_login_saves_telegram_language(client, factory):
    user = await factory.User(language_code=None)

    response = await client.post(
        "/api/auth/login",
        json={"init_data": signed_init_data(user.tg_id, language_code="ru-RU")},
    )

    assert response.status_code == 200
    async with async_session_maker() as session:
        stored_user = await session.scalar(select(User).where(User.id == user.id))
    assert stored_user.language_code == "ru-ru"


@pytest.mark.asyncio
@pytest.mark.parametrize("age", [600, -120])
async def test_miniapp_login_rejects_expired_or_future_launch(client, factory, age):
    user = await factory.User()
    response = await client.post(
        "/api/auth/login", json={"init_data": signed_init_data(user.tg_id, age)}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_miniapp_login_rejects_tampered_launch(client, factory):
    user = await factory.User()
    data = signed_init_data(user.tg_id) + "&auth_date=1"
    response = await client.post("/api/auth/login", json={"init_data": data})
    assert response.status_code == 401
