#!/usr/bin/env python3
"""Create a SQLAdmin superuser through an interactive terminal prompt."""

import asyncio
import getpass

from sqlalchemy import select

from src.database import AdminUser, async_session_maker


async def create_superuser() -> None:
    username = input("Username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")
    if len(username) > 64:
        raise SystemExit("Username must be 64 characters or fewer.")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Password (again): ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    async with async_session_maker() as session:
        existing = await session.scalar(
            select(AdminUser).where(AdminUser.username == username)
        )
        if existing is not None:
            raise SystemExit(f"Superuser '{username}' already exists.")

        session.add(
            AdminUser(
                username=username,
                password_hash=AdminUser.hash_password(password),
                is_superuser=True,
            )
        )
        await session.commit()

    print(f"Superuser '{username}' created.")


if __name__ == "__main__":
    asyncio.run(create_superuser())
