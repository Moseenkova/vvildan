import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Table,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from src.config import get_settings


engine = create_async_engine(get_settings().DATABASE_URL)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str]
    phone: Mapped[Optional[str]]
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user")
    requests: Mapped[list["Request"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("tg_id"),)


class RequestStatus(enum.Enum):
    active = "active"
    cancelled = "cancelled"
    completed = "completed"
    expired = "expired"


request_departure_cities = Table(
    "request_departure_cities",
    Base.metadata,
    Column("request_id", ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True),
    Column("city_id", ForeignKey("cities.id", ondelete="CASCADE"), primary_key=True),
)


request_arrival_cities = Table(
    "request_arrival_cities",
    Base.metadata,
    Column("request_id", ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True),
    Column("city_id", ForeignKey("cities.id", ondelete="CASCADE"), primary_key=True),
)


class RequestRole(enum.Enum):
    sender = "sender"
    courier = "courier"


class Request(Base):
    __tablename__ = "requests"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    user: Mapped["User"] = relationship(back_populates="requests")
    role: Mapped[RequestRole] = mapped_column(Enum(RequestRole), index=True)

    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)

    departure_cities: Mapped[list["City"]] = relationship(
        secondary=request_departure_cities,
        back_populates="departure_requests",
    )
    arrival_cities: Mapped[list["City"]] = relationship(
        secondary=request_arrival_cities,
        back_populates="arrival_requests",
    )

    comment: Mapped[str] = mapped_column(default="", server_default="")
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus),
        default=RequestStatus.active,
        server_default=RequestStatus.active.value,
        index=True,
    )
    sender_matches: Mapped[list["Match"]] = relationship(
        back_populates="sender_request",
        foreign_keys="Match.sender_request_id",
        cascade="all, delete-orphan",
    )
    courier_matches: Mapped[list["Match"]] = relationship(
        back_populates="courier_request",
        foreign_keys="Match.courier_request_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("date_from <= date_to", name="ck_requests_date_range"),
    )


class MatchStatus(enum.Enum):
    proposed = "proposed"
    contacted = "contacted"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"


class Match(Base):
    __tablename__ = "matches"

    sender_request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"),
    )
    sender_request: Mapped["Request"] = relationship(
        back_populates="sender_matches", foreign_keys=[sender_request_id]
    )
    courier_request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"),
    )
    courier_request: Mapped["Request"] = relationship(
        back_populates="courier_matches", foreign_keys=[courier_request_id]
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus),
        default=MatchStatus.proposed,
        server_default=MatchStatus.proposed.value,
    )

    __table_args__ = (
        UniqueConstraint(
            "sender_request_id",
            "courier_request_id",
        ),
        CheckConstraint(
            "sender_request_id <> courier_request_id",
            name="ck_matches_different_requests",
        ),
    )


class Country(Base):
    __tablename__ = "countries"
    name: Mapped[str]
    iso_code: Mapped[Optional[str]] = mapped_column(unique=True)
    cities: Mapped[List["City"]] = relationship(back_populates="country")
    localized_names: Mapped[List["CountryName"]] = relationship(
        back_populates="country", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("name"),)


class City(Base):
    __tablename__ = "cities"
    name: Mapped[str]
    population: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship(back_populates="cities")
    localized_names: Mapped[List["CityName"]] = relationship(
        back_populates="city", cascade="all, delete-orphan"
    )
    departure_requests: Mapped[List["Request"]] = relationship(
        secondary=request_departure_cities,
        back_populates="departure_cities",
    )
    arrival_requests: Mapped[List["Request"]] = relationship(
        secondary=request_arrival_cities,
        back_populates="arrival_cities",
    )

    __table_args__ = (UniqueConstraint("country_id", "name"),)


class CountryName(Base):
    __tablename__ = "country_names"
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    language_code: Mapped[str] = mapped_column(index=True)
    name: Mapped[str]
    country: Mapped["Country"] = relationship(back_populates="localized_names")

    __table_args__ = (
        UniqueConstraint("country_id", "language_code", "name"),
        Index("ix_country_names_language_name", "language_code", "name"),
    )


class CityName(Base):
    __tablename__ = "city_names"
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), index=True
    )
    language_code: Mapped[str] = mapped_column(index=True)
    name: Mapped[str]
    city: Mapped["City"] = relationship(back_populates="localized_names")

    __table_args__ = (
        UniqueConstraint("city_id", "language_code", "name"),
        Index("ix_city_names_language_name", "language_code", "name"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    token_id: Mapped[str] = mapped_column(unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
    expire: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CustomerTgTopic(Base):
    __tablename__ = "customer_tg_topics"

    customer_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    topic_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)


async def get_or_create(session, model, defaults=None, **kwargs):
    params = {**kwargs, **(defaults or {})}
    query = (
        insert(model)
        .values(**params)
        .on_conflict_do_nothing()
        .returning(model)
    )
    result = await session.execute(query)
    instance = result.scalars().one_or_none()

    if instance is not None:
        await session.commit()
        return instance, True

    result = await session.execute(select(model).filter_by(**kwargs))
    return result.scalars().one(), False
