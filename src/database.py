import enum
from datetime import date, datetime
from os import getenv
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    UniqueConstraint,
    func,
    insert,
    select,
)
from sqlalchemy.dialects.postgresql import JSON
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
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user")

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
class BaggageKind(enum.StrEnum):
    usual = "usual"
    liquid = "liquid"
    expensive = "expensive"
    document = "document"
    troublesome = "troublesome"
    other = "other"


RU_LABELS = {
    BaggageKind.usual: "Обычный",
    BaggageKind.liquid: "Жидкость",
    BaggageKind.document: "Документ",
    BaggageKind.troublesome: "Проблемный",
    BaggageKind.usual: "Обычный",
}


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
    origin_id: Mapped[int] = mapped_column(ForeignKey("airports.id"))
    destination_id: Mapped[int] = mapped_column(ForeignKey("airports.id"))

    origin: Mapped["Airport"] = relationship(
        foreign_keys=[origin_id], back_populates="requests_from"
    )
    destination: Mapped["Airport"] = relationship(
        foreign_keys=[destination_id], back_populates="requests_to"
    )
    date: Mapped[date] = mapped_column(Date, nullable=True)
    date_to: Mapped[date] = mapped_column(Date, nullable=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=True)
    baggage_types: Mapped[list] = mapped_column(JSON, nullable=False)
    comment: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column(Enum(Status))


class Country(Base):
    __tablename__ = "countries"
    name: Mapped[str]
    iso_code: Mapped[Optional[str]] = mapped_column(unique=True)
    is_viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    cities: Mapped[List["City"]] = relationship(back_populates="country")

    __table_args__ = (UniqueConstraint("name"),)


class City(Base):
    __tablename__ = "cities"
    name: Mapped[str]
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship(back_populates="cities")
    is_viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    airports: Mapped[List["Airport"]] = relationship(back_populates="city")

    __table_args__ = (UniqueConstraint("country_id", "name"),)


class Airport(Base):
    __tablename__ = "airports"
    ident: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    airport_type: Mapped[str]
    iata_code: Mapped[Optional[str]] = mapped_column(index=True)
    icao_code: Mapped[Optional[str]] = mapped_column(index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    scheduled_service: Mapped[bool] = mapped_column(Boolean, default=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)
    city: Mapped["City"] = relationship(back_populates="airports")
    requests_from: Mapped[List["Request"]] = relationship(
        foreign_keys="Request.origin_id", back_populates="origin"
    )
    requests_to: Mapped[List["Request"]] = relationship(
        foreign_keys="Request.destination_id", back_populates="destination"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    token_id: Mapped[str] = mapped_column(unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
    expire: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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
