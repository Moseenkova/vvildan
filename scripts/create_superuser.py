#!/usr/bin/env python3
"""Promote an existing Telegram user to SQLAdmin superuser interactively."""

import asyncio
import getpass

from sqlalchemy import select

from src.database import User, async_session_maker


async def create_superuser() -> None:
    try:
        tg_id = int(input("Telegram ID (tg_id): ").strip())
    except ValueError:
        raise SystemExit("Telegram ID must be an integer.") from None
    if not 0 < tg_id <= 2**63 - 1:
        raise SystemExit("Telegram ID must be a positive 64-bit integer.")

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user is None:
            raise SystemExit(f"No user found with Telegram ID {tg_id}.")
        if user.is_superuser:
            raise SystemExit(f"User with Telegram ID {tg_id} is already a superuser.")

        username = input("Username: ").strip()
        if not username:
            raise SystemExit("Username cannot be empty.")
        if len(username) > 64:
            raise SystemExit("Username must be 64 characters or fewer.")

        existing = await session.scalar(
            select(User).where(User.username == username, User.id != user.id)
        )
        if existing is not None:
            raise SystemExit(f"Username '{username}' is already taken.")

        password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Password (again): ")
        if not password:
            raise SystemExit("Password cannot be empty.")
        if password != confirmation:
            raise SystemExit("Passwords do not match.")

        user.username = username
        user.password_hash = User.hash_password(password)
        user.is_superuser = True
        await session.commit()

    print(f"Superuser '{username}' created for Telegram ID {tg_id}.")


if __name__ == "__main__":
    asyncio.run(create_superuser())
