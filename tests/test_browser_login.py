import hashlib
import hmac
import time

import pytest

from src.config import get_settings


def signed_payload(user_id, age=0):
    data = {"id": user_id, "first_name": "Browser user", "auth_date": int(time.time()) - age}
    secret = hashlib.sha256(get_settings().BOT_TOKEN.get_secret_value().encode()).digest()
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return data


@pytest.mark.asyncio
async def test_browser_login_returns_usable_token(client, factory):
    user = await factory.User()
    response = await client.post('/api/auth/telegram', json=signed_payload(user.tg_id))
    assert response.status_code == 200
    assert get_settings().REFRESH_COOKIE_NAME in response.cookies
    requests = await client.get('/api/requests', headers={
        'Authorization': f'Bearer {response.json()["access_token"]}'
    })
    assert requests.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['tampered', 'expired', 'future'])
async def test_browser_login_rejects_invalid_credentials(client, factory, kind):
    user = await factory.User()
    age = {'tampered': 0, 'expired': 600, 'future': -120}[kind]
    data = signed_payload(user.tg_id, age)
    if kind == 'tampered':
        data['id'] += 1
    response = await client.post('/api/auth/telegram', json=data)
    assert response.status_code == 401
    assert get_settings().REFRESH_COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_browser_login_requires_registered_user(client):
    response = await client.post('/api/auth/telegram', json=signed_payload(999999))
    assert response.status_code == 404
