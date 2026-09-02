from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import get_settings

cfg = get_settings()
if cfg.MODE != "TEST":
    raise RuntimeError("Tests must be run with MODE=TEST")

from src.database import Base, User, async_session_maker, engine  # noqa: E402
from src.main import app  # noqa: E402
from tests.factories import FactoryNamespace, build_factory_namespace  # noqa: E402


@dataclass
class AuthenticatedClient:
    client: AsyncClient
    current_user: User


@pytest_asyncio.fixture(scope="function", autouse=True)
async def database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def factory(database) -> AsyncIterator[FactoryNamespace]:
    async with async_session_maker() as session:
        yield build_factory_namespace(session)


@pytest_asyncio.fixture(scope="function")
async def client(database) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest_asyncio.fixture(scope="function")
async def auth_ac(
    factory: FactoryNamespace,
) -> AsyncIterator[AuthenticatedClient]:
    assert cfg.DEV_CHAT_ID is not None
    current_user = await factory.User(tg_id=cfg.DEV_CHAT_ID)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/auth/dev-login")

        assert response.status_code == 200
        assert ac.cookies[cfg.REFRESH_COOKIE_NAME]
        access_token = response.json()["access_token"]
        ac.headers = {"Authorization": f"Bearer {access_token}"}

        yield AuthenticatedClient(client=ac, current_user=current_user)
