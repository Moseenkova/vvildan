#!/usr/bin/env python3
"""Download selected OurAirports data and import it into the application database."""

import argparse
import asyncio
import csv
import io
import sys
from pathlib import Path
from urllib.request import urlopen

from sqlalchemy import func, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
COUNTRIES_URL = "https://davidmegginson.github.io/ourairports-data/countries.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "international_and_large_airports.csv"

# OurAirports uses district-level municipalities for these airports, but the
# application searches and groups locations at city level.
CITY_BY_AIRPORT_IDENT = {
    "CN-0154": "Hangzhou",
    "EDFH": "Frankfurt am Main",
    "EGSS": "London",
    "ESOW": "Stockholm",
    "FNBJ": "Luanda",
    "KCVG": "Cincinnati",
    "KDFW": "Dallas",
    "KRFD": "Chicago",
    "LFPG": "Paris",
    "LFPO": "Paris",
    "LTBA": "Istanbul",
    "LTFJ": "Istanbul",
    "MSLP": "San Salvador",
    "NWWW": "Nouméa",
    "OMDW": "Dubai",
    "SAEZ": "Buenos Aires",
    "SBGL": "Rio de Janeiro",
    "VN-0018": "Ho Chi Minh City",
    "YMAV": "Melbourne",
    "YSSY": "Sydney",
    "ZMCK": "Ulaanbaatar",
    "ZPCW": "Lincang",
}

OUTPUT_FIELDS = [
    "ident",
    "name",
    "type",
    "municipality",
    "iso_country",
    "country_name",
    "iata_code",
    "gps_code",
    "latitude_deg",
    "longitude_deg",
    "scheduled_service",
]


def download_csv(url: str) -> list[dict[str, str]]:
    with urlopen(url, timeout=60) as response:
        content = response.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))


def select_airports(
    airports: list[dict[str, str]], countries: dict[str, str]
) -> list[dict[str, str]]:
    selected = []
    for airport in airports:
        is_large = airport["type"] == "large_airport"
        is_international = (
            airport["type"] == "medium_airport"
            and airport["scheduled_service"] == "yes"
            and (
                bool(airport["iata_code"]) or "international" in airport["name"].lower()
            )
        )
        if not (is_large or is_international):
            continue
        if not airport["municipality"] or airport["iso_country"] not in countries:
            continue

        selected.append(
            {
                field: countries[airport["iso_country"]]
                if field == "country_name"
                else airport[field]
                for field in OUTPUT_FIELDS
            }
        )
    return selected


def save_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def city_name_for_airport(row: dict[str, str]) -> str:
    return CITY_BY_AIRPORT_IDENT.get(row["ident"], row["municipality"])


async def import_rows(rows: list[dict[str, str]]) -> tuple[int, int, int]:
    from src.database import Airport, City, Country, async_session_maker

    async with async_session_maker() as session:
        countries = (await session.scalars(select(Country))).all()
        countries_by_code = {
            country.iso_code: country for country in countries if country.iso_code
        }
        countries_by_name = {country.name: country for country in countries}

        for row in rows:
            code = row["iso_country"]
            country = countries_by_code.get(code) or countries_by_name.get(
                row["country_name"]
            )
            if country is None:
                country = Country(name=row["country_name"], iso_code=code)
                session.add(country)
                countries_by_name[country.name] = country
            else:
                country.name = row["country_name"]
                country.iso_code = code
            countries_by_code[code] = country

        await session.flush()

        cities = (await session.scalars(select(City))).all()
        cities_by_key = {(city.country_id, city.name): city for city in cities}
        for row in rows:
            country = countries_by_code[row["iso_country"]]
            key = (country.id, city_name_for_airport(row))
            if key not in cities_by_key:
                city = City(name=key[1], country=country)
                session.add(city)
                cities_by_key[key] = city

        await session.flush()

        airports = (await session.scalars(select(Airport))).all()
        airports_by_ident = {airport.ident: airport for airport in airports}
        for row in rows:
            country = countries_by_code[row["iso_country"]]
            city = cities_by_key[(country.id, city_name_for_airport(row))]
            values = {
                "name": row["name"],
                "airport_type": row["type"],
                "iata_code": row["iata_code"] or None,
                "icao_code": row["gps_code"] or None,
                "latitude": float(row["latitude_deg"]),
                "longitude": float(row["longitude_deg"]),
                "scheduled_service": row["scheduled_service"] == "yes",
                "city": city,
            }
            airport = airports_by_ident.get(row["ident"])
            if airport is None:
                airport = Airport(ident=row["ident"], **values)
                session.add(airport)
                airports_by_ident[airport.ident] = airport
            else:
                for field, value in values.items():
                    setattr(airport, field, value)

        await session.commit()
        country_count = await session.scalar(select(func.count()).select_from(Country))
        city_count = await session.scalar(select(func.count()).select_from(City))
        airport_count = await session.scalar(select(func.count()).select_from(Airport))
        return country_count or 0, city_count or 0, airport_count or 0


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    airport_rows, country_rows = await asyncio.gather(
        asyncio.to_thread(download_csv, AIRPORTS_URL),
        asyncio.to_thread(download_csv, COUNTRIES_URL),
    )
    countries = {row["code"]: row["name"] for row in country_rows}
    selected = select_airports(airport_rows, countries)
    save_csv(selected, args.output)
    print(f"Downloaded {len(selected)} airports to {args.output}")

    if not args.download_only:
        country_count, city_count, airport_count = await import_rows(selected)
        print(
            f"Database totals: {country_count} countries, {city_count} cities, "
            f"{airport_count} airports"
        )


if __name__ == "__main__":
    asyncio.run(main())
