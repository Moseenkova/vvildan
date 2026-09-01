from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

from factory.base import Factory
from factory.declarations import PostGeneration, Sequence, SubFactory
from factory.faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import (
    City,
    Country,
    Request,
    RequestRole,
    RequestStatus,
    User,
)

Model = TypeVar("Model")


class BaseFactory(Factory):
    pass


class UserFactory(BaseFactory):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = User

    id = None
    tg_id = Sequence(lambda sequence: 9_000_000_000 + sequence)
    name = Faker("name")
    phone = Faker("phone_number")


class CountryFactory(BaseFactory):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Country

    id = None
    name = Sequence(lambda sequence: f"Country {sequence}")
    iso_code = Sequence(lambda sequence: f"T{sequence}")


class CityFactory(BaseFactory):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = City

    id = None
    name = Sequence(lambda sequence: f"City {sequence}")
    population = Faker("random_int", min=1, max=20_000_000)
    country = SubFactory(CountryFactory)


def _set_departure_cities(
    request: Request,
    create: bool,
    extracted: Iterable[City] | None,
    **kwargs: Any,
) -> None:
    if extracted:
        request.departure_cities.extend(extracted)


def _set_arrival_cities(
    request: Request,
    create: bool,
    extracted: Iterable[City] | None,
    **kwargs: Any,
) -> None:
    if extracted:
        request.arrival_cities.extend(extracted)


class RequestFactory(BaseFactory):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Request

    id = None
    user = SubFactory(UserFactory)
    role = RequestRole.sender
    date_from = date(2026, 9, 1)
    date_to = date(2026, 9, 2)
    comment = Faker("sentence")
    status = RequestStatus.active
    departure_cities = PostGeneration(_set_departure_cities)
    arrival_cities = PostGeneration(_set_arrival_cities)


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
    Request: AsyncFactoryCall


def build_factory_namespace(session: AsyncSession) -> FactoryNamespace:
    return FactoryNamespace(
        User=AsyncModelFactory[User](session, UserFactory),
        Country=AsyncModelFactory[Country](session, CountryFactory),
        City=AsyncModelFactory[City](session, CityFactory),
        Request=AsyncModelFactory[Request](session, RequestFactory),
    )
