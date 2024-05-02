from os import getenv

from dotenv import load_dotenv
from sqlalchemy import BigInteger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()
DATABASE_URL = getenv("DATABASE_URL")


engine = create_async_engine(DATABASE_URL)

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# created_at


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str]
