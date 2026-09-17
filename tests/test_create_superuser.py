import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from scripts.create_superuser import create_superuser
from src.database import User, async_session_maker


@pytest.mark.asyncio
async def test_promotes_existing_user(monkeypatch, factory):
    user = await factory.User(username="admin", name="Original", phone="123")
    answers = iter([str(user.tg_id), "admin"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _: "password")

    await create_superuser()

    async with async_session_maker() as session:
        saved = await session.get(User, user.id)
        assert saved.is_superuser
        assert saved.verify_password("password")
        assert (saved.tg_id, saved.name, saved.phone) == (user.tg_id, "Original", "123")
        assert await session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.asyncio
async def test_missing_user(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "123")
    with pytest.raises(SystemExit, match="No user found"):
        await create_superuser()


@pytest.mark.asyncio
async def test_taken_username(monkeypatch, factory):
    user = await factory.User()
    await factory.User(username="taken")
    answers = iter([str(user.tg_id), "taken"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    with pytest.raises(SystemExit, match="already taken"):
        await create_superuser()
    async with async_session_maker() as session:
        assert not (await session.get(User, user.id)).is_superuser


@pytest.mark.asyncio
async def test_telegram_id_is_unique(factory):
    user = await factory.User()
    async with async_session_maker() as session:
        session.add(User(tg_id=user.tg_id, name="Duplicate"))
        with pytest.raises(IntegrityError):
            await session.commit()
