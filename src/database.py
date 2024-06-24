import enum
from datetime import date, datetime
from os import getenv
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    func,
    insert,
    select,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

load_dotenv()
DATABASE_URL = getenv("DATABASE_URL")


engine = create_async_engine(DATABASE_URL)

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str]
    phone: Mapped[Optional[int]]
    courier: Mapped["Courier"] = relationship(back_populates="user")
    sender: Mapped["Sender"] = relationship(back_populates="user")

    __table_args__ = (UniqueConstraint("tg_id"),)


class Courier(Base):
    __tablename__ = "couriers"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="courier")

    __table_args__ = (UniqueConstraint("user_id"),)


class Sender(Base):
    __tablename__ = "senders"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="sender")
    requests: Mapped["Request"] = relationship(back_populates="sender")

    __table_args__ = (UniqueConstraint("user_id"),)


class BaggageKind(enum.Enum):
    usual = 1
    liquid = 2
    expensive = 3
    document = 4
    troublesome = 5


class VolumeKind(enum.Enum):
    kilo = 1
    liter = 2
    piece = 3


class Status(enum.Enum):
    new = 1
    pending = 2
    accepted = 3
    rejected = 4
    fulfilled = 5


class Request(Base):
    __tablename__ = "requests"
    sender_id: Mapped[int] = mapped_column(ForeignKey("senders.id"))
    sender: Mapped["Sender"] = relationship(back_populates="requests")
    origin: Mapped[str]
    destination: Mapped[str]
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    baggage_kind: Mapped[str] = mapped_column(Enum(BaggageKind))
    volume_kind: Mapped[str] = mapped_column(Enum(VolumeKind))
    volume: Mapped[int]
    status: Mapped[str] = mapped_column(Enum(Status))


class Country(Base):
    __tablename__ = "countries"
    name: Mapped[str]
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    cities: Mapped["City"] = relationship(back_populates="country")

    __table_args__ = (UniqueConstraint("name"),)


class City(Base):
    __tablename__ = "cities"
    name: Mapped[str]
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship(back_populates="cities")

    __table_args__ = (UniqueConstraint("name"),)


async def get_or_create(session, model, defaults=None, **kwargs):
    if defaults is None:
        defaults = {}

    try:
        query = select(model).filter_by(**kwargs)
        result = await session.execute(query)
        instance = result.scalars().one()
        return instance, False
    except NoResultFound:
        params = {**kwargs, **defaults}
        query = insert(model).values(**params).returning(model)
        result = await session.execute(query)
        await session.commit()
        instance = result.scalars().one()
        return instance, True
