from sqlalchemy import func, or_, select

from src.database import async_session_maker, City, CityName, Country, CountryName


async def find_cities(term: str, language: str):
    term = term.strip()
    if not term:
        return []

    search = f"%{term}%"
    language = language.lower().replace("_", "-").split("-", 1)[0]

    localized_city_name = (
        select(func.min(CityName.name))
        .where(CityName.city_id == City.id, CityName.language_code == language)
        .correlate(City)
        .scalar_subquery()
    )
    english_city_name = (
        select(func.min(CityName.name))
        .where(CityName.city_id == City.id, CityName.language_code == "en")
        .correlate(City)
        .scalar_subquery()
    )
    english_country_name = (
        select(func.min(CountryName.name))
        .where(
            CountryName.country_id == Country.id,
            CountryName.language_code == "en",
        )
        .correlate(Country)
        .scalar_subquery()
    )
    localized_country_name = (
        select(func.min(CountryName.name))
        .where(
            CountryName.country_id == Country.id,
            CountryName.language_code == language,
        )
        .correlate(Country)
        .scalar_subquery()
    )

    query = (
        select(
            City.id,
            func.coalesce(localized_city_name, english_city_name, City.name).label(
                "name"
            ),
            Country.id.label("country_id"),
            func.coalesce(
                localized_country_name,
                english_country_name,
                Country.name,
            ).label("country_name"),
        )
        .join(Country, City.country_id == Country.id)
        .where(
            or_(
                City.name.ilike(search),
                Country.name.ilike(search),
                City.localized_names.any(CityName.name.ilike(search)),
                Country.localized_names.any(CountryName.name.ilike(search)),
            )
        )
        .order_by(
            City.population.desc(),
            "country_name",
            "name",
        )
        .limit(50)
    )

    async with async_session_maker() as session:
        result = await session.execute(query)
        return result.mappings().all()
