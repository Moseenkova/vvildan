from sqlalchemy import select, delete
from src.database import async_session_maker, User, RefreshToken

class UserDAO:
    @classmethod
    async def find_one_or_none(cls, *filters):
        async with async_session_maker() as session:
            query = select(User).filter(*filters)
            result = await session.execute(query)
            return result.scalars().one_or_none()

    @classmethod
    async def get_by_user_id(cls, id: int):
        return await cls.find_one_or_none(User.id == id)

    @classmethod
    async def get_by_tg_id(cls, tg_id: int):
        return await cls.find_one_or_none(User.tg_id == tg_id)


class RefreshTokenDAO:
    @classmethod
    async def find_one_or_none(cls, *filters):
        async with async_session_maker() as session:
            query = select(RefreshToken).filter(*filters)
            result = await session.execute(query)
            return result.scalars().one_or_none()
            
    @classmethod
    async def create(cls, data: dict):
        async with async_session_maker() as session:
            new_token = RefreshToken(**data)
            session.add(new_token)
            await session.commit()
            return new_token

    @classmethod
    async def delete(cls, *filters):
        async with async_session_maker() as session:
            query = delete(RefreshToken).filter(*filters)
            await session.execute(query)
            await session.commit()
