from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

import factory
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import (
    Airport,
    City,
    Country,
    Request,
    RequestRole,
    RequestStatus,
    User,
)

Model = TypeVar("Model")


class BaseFactory(factory.Factory):
    class Meta:
        abstract = True


class UserFactory(BaseFactory):
    class Meta:
        model = User

    id = None
    tg_id = factory.Sequence(lambda sequence: 9_000_000_000 + sequence)
    name = factory.Faker("name")
    phone = factory.Faker("phone_number")


class CountryFactory(BaseFactory):
    class Meta:
        model = Country

    id = None
    name = factory.Sequence(lambda sequence: f"Country {sequence}")
    iso_code = factory.Sequence(lambda sequence: f"T{sequence}")


class CityFactory(BaseFactory):
    class Meta:
        model = City

    id = None
    name = factory.Sequence(lambda sequence: f"City {sequence}")
    population = factory.Faker("random_int", min=1, max=20_000_000)
    country = factory.SubFactory(CountryFactory)


class AirportFactory(BaseFactory):
    class Meta:
        model = Airport

    id = None
    ident = factory.Sequence(lambda sequence: f"TEST-{sequence}")
    name = factory.Sequence(lambda sequence: f"Airport {sequence}")
    airport_type = "large_airport"
    iata_code = factory.Sequence(lambda sequence: f"T{sequence:02d}"[-3:])
    icao_code = factory.Sequence(lambda sequence: f"TT{sequence:02d}"[-4:])
    latitude = factory.Faker("latitude")
    longitude = factory.Faker("longitude")
    scheduled_service = True
    city = factory.SubFactory(CityFactory)


class RequestFactory(BaseFactory):
    class Meta:
        model = Request

    id = None
    user = factory.SubFactory(UserFactory)
    role = RequestRole.sender
    date_from = date(2026, 9, 1)
    date_to = date(2026, 9, 2)
    comment = factory.Faker("sentence")
    status = RequestStatus.active

    @factory.post_generation
    def departure_airports(self, create, extracted, **kwargs):
        if extracted:
            self.departure_airports.extend(extracted)

    @factory.post_generation
    def arrival_airports(self, create, extracted, **kwargs):
        if extracted:
            self.arrival_airports.extend(extracted)


class AsyncModelFactory(Generic[Model]):
    def __init__(self, session: AsyncSession, model_factory: type[BaseFactory]) -> None:
        self.session = session
        self.model_factory = model_factory

    async def __call__(self, **kwargs: Any) -> Model:
        instance = self.model_factory.build(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        return instance


AsyncFactoryCall = Callable[..., Awaitable[Any]]


@dataclass
class FactoryNamespace:
    User: AsyncFactoryCall
    Country: AsyncFactoryCall
    City: AsyncFactoryCall
    Airport: AsyncFactoryCall
    Request: AsyncFactoryCall


def build_factory_namespace(session: AsyncSession) -> FactoryNamespace:
    return FactoryNamespace(
        User=AsyncModelFactory[User](session, UserFactory),
        Country=AsyncModelFactory[Country](session, CountryFactory),
        City=AsyncModelFactory[City](session, CityFactory),
        Airport=AsyncModelFactory[Airport](session, AirportFactory),
        Request=AsyncModelFactory[Request](session, RequestFactory),
    )
