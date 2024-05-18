from datetime import datetime
from os import getenv

from dotenv import load_dotenv
from sqlalchemy import BigInteger, Date, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()
DATABASE_URL = getenv("DATABASE_URL")


engine = create_async_engine(DATABASE_URL)

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)


# created_at


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True
    )  # unik value,в таблице юзер не должен повтараться
    name: Mapped[str]


class Courier(Base):
    __tablename__ = "couriers"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"))
    phone: Mapped[int]


class Sender(Base):
    __tablename__ = "senders"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"))
    phone: Mapped[int]


class Request(Base):
    __tablename__ = "requests"
    sender_id: Mapped[int] = mapped_column(ForeignKey("senders.id"))
    from_: Mapped[str]
    to: Mapped[str]
    date_from: Mapped[datetime] = mapped_column(Date)
    date_to: Mapped[datetime] = mapped_column(Date)
    courier_id: Mapped[int] = mapped_column(ForeignKey("courier_id"))


Base.metadata.create_all(engine)
