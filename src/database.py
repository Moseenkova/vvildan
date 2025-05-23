import enum
from datetime import date, datetime
from os import getenv
from typing import List, Optional

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
    requests = relationship("Request", back_populates="courier")

    __table_args__ = (UniqueConstraint("user_id"),)


class Sender(Base):
    __tablename__ = "senders"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="sender")
    requests: Mapped["Request"] = relationship(back_populates="sender")
    requests = relationship("Request", back_populates="sender")

    __table_args__ = (UniqueConstraint("user_id"),)


# TODO может быть наоброт порядок
class BaggageKind(enum.Enum):
    usual = "Обычный"
    liquid = "Жидкость"
    expensive = "Ценный"
    document = "Документ"
    troublesome = "Проблемный"
    other = "Другое"


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
    sender_id: Mapped[int] = mapped_column(ForeignKey("senders.id"), nullable=True)
    sender: Mapped["Sender"] = relationship(back_populates="requests")
    courier_id: Mapped[int] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    courier: Mapped["Courier"] = relationship(back_populates="requests")
    origin_id: Mapped[int] = mapped_column(ForeignKey("user_cities.id"))
    destination_id: Mapped[int] = mapped_column(ForeignKey("user_cities.id"))

    origin: Mapped["UserCity"] = relationship(
        foreign_keys=[origin_id], backref="requests_from"
    )
    destination: Mapped["UserCity"] = relationship(
        foreign_keys=[destination_id], backref="requests_to"
    )
    date: Mapped[date] = mapped_column(Date)
    baggage_types: Mapped[str]
    comment: Mapped[str]
    status: Mapped[str] = mapped_column(Enum(Status))


class Country(Base):
    __tablename__ = "countries"
    name: Mapped[str]
    cities: Mapped["City"] = relationship(back_populates="country")

    __table_args__ = (UniqueConstraint("name"),)


class City(Base):
    __tablename__ = "cities"
    name: Mapped[str]
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship(back_populates="cities")
    user_cities: Mapped[List["UserCity"]] = relationship(back_populates="city")

    __table_args__ = (UniqueConstraint("name"),)


class UserCity(Base):
    __tablename__ = "user_cities"
    name: Mapped[str]
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    city_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cities.id"))
    city: Mapped[Optional["City"]] = relationship(back_populates="user_cities")

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
