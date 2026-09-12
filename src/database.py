import enum
import hashlib
import hmac
import os
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.config import Settings, get_settings

cfg: Settings = get_settings()

engine = create_async_engine(cfg.DATABASE_URL)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str]
    phone: Mapped[Optional[str]]
    username: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, default=None
    )
    language_code: Mapped[Optional[str]] = mapped_column(String(16), default=None)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256), default=None)
    is_superuser: Mapped[bool] = mapped_column(default=False, server_default="false")
    matches_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user")
    requests: Mapped[list["Request"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("tg_id"),)

    def __str__(self) -> str:
        return self.username or self.name

    @staticmethod
    def hash_password(password: str) -> str:
        salt = os.urandom(16)
        iterations = 600_000
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"

    def verify_password(self, password: str) -> bool:
        if self.password_hash is None:
            return False
        try:
            algorithm, iterations, salt, expected = self.password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
            ).hex()
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(actual, expected)


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

    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)

    departure_cities: Mapped[list["City"]] = relationship(
        secondary=request_departure_cities,
        back_populates="departure_requests",
    )
    arrival_cities: Mapped[list["City"]] = relationship(
        secondary=request_arrival_cities,
        back_populates="arrival_requests",
    )

    comment: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
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
        CheckConstraint(
            "date_from IS NOT NULL OR date_to IS NOT NULL",
            name="ck_requests_has_date",
        ),
    )

    def __str__(self) -> str:
        return f"{self.role.value} #{self.id}: {self.date_from} – {self.date_to}"


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
    sender_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    courier_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

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

    def __str__(self) -> str:
        return f"Match #{self.id} ({self.status.value})"


class Country(Base):
    __tablename__ = "countries"
    name: Mapped[str]
    iso_code: Mapped[Optional[str]] = mapped_column(unique=True)
    cities: Mapped[List["City"]] = relationship(back_populates="country")
    localized_names: Mapped[List["CountryName"]] = relationship(
        back_populates="country", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("name"),)

    def __str__(self) -> str:
        return self.name


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

    def __str__(self) -> str:
        return self.name


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

    def __str__(self) -> str:
        return f"{self.name} ({self.language_code})"


class CityName(Base):
    __tablename__ = "city_names"
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    language_code: Mapped[str] = mapped_column(index=True)
    name: Mapped[str]
    city: Mapped["City"] = relationship(back_populates="localized_names")

    __table_args__ = (
        UniqueConstraint("city_id", "language_code", "name"),
        Index("ix_city_names_language_name", "language_code", "name"),
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.language_code})"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    token_id: Mapped[str] = mapped_column(unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
    expire: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __str__(self) -> str:
        return f"Refresh token #{self.id}"


class CustomerTgTopic(Base):
    __tablename__ = "customer_tg_topics"

    customer_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    topic_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    language_code: Mapped[Optional[str]]
    last_openai_response_id: Mapped[Optional[str]] = mapped_column(String(255))

    def __str__(self) -> str:
        return f"Chat {self.customer_chat_id} / topic {self.topic_id}"


async def get_or_create(session, model, defaults=None, **kwargs):
    params = {**kwargs, **(defaults or {})}
    query = insert(model).values(**params).on_conflict_do_nothing().returning(model)
    result = await session.execute(query)
    instance = result.scalars().one_or_none()

    if instance is not None:
        await session.commit()
        return instance, True

    result = await session.execute(select(model).filter_by(**kwargs))
    return result.scalars().one(), False
