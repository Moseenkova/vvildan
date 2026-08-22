#!/usr/bin/env python3
"""Import localized location aliases from a UTF-8 CSV file.

Required columns: entity_type, entity_key, language_code, name.

Keys are an ISO country code (country), ``ISO|English city name`` (city), or an
OurAirports ident (airport). Running the importer repeatedly is safe.
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"entity_type", "entity_key", "language_code", "name"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
    return rows


async def import_rows(rows: list[dict[str, str]]) -> tuple[int, int]:
    from src.database import (
        Airport,
        AirportName,
        async_session_maker,
        City,
        CityName,
        Country,
        CountryName,
    )

    async with async_session_maker() as session:
        countries = (await session.scalars(select(Country))).all()
        cities = (await session.scalars(select(City))).all()
        airports = (await session.scalars(select(Airport))).all()

        countries_by_code = {
            country.iso_code.upper(): country
            for country in countries
            if country.iso_code
        }
        country_codes_by_id = {
            country.id: country.iso_code.upper()
            for country in countries
            if country.iso_code
        }
        city_by_key = {
            f"{country_codes_by_id[city.country_id]}|{city.name}": city
            for city in cities
            if city.country_id in country_codes_by_id
        }
        airports_by_ident = {airport.ident.upper(): airport for airport in airports}

        model_and_entities = {
            "country": (CountryName, countries_by_code, "country"),
            "city": (CityName, city_by_key, "city"),
            "airport": (AirportName, airports_by_ident, "airport"),
        }
        existing = {
            (model.__tablename__, alias_id, code, name)
            for model, foreign_key in (
                (CountryName, "country_id"),
                (CityName, "city_id"),
                (AirportName, "airport_id"),
            )
            for alias_id, code, name in (
                await session.execute(
                    select(getattr(model, foreign_key), model.language_code, model.name)
                )
            ).all()
        }

        imported = 0
        skipped = 0
        for row_number, row in enumerate(rows, start=2):
            entity_type = row["entity_type"].strip().lower()
            config = model_and_entities.get(entity_type)
            if config is None:
                raise ValueError(f"Row {row_number}: unknown entity_type {entity_type!r}")
            model, entities, relationship_name = config
            raw_key = row["entity_key"].strip()
            key = raw_key.upper() if entity_type != "city" else raw_key
            entity = entities.get(key)
            if entity is None:
                raise ValueError(f"Row {row_number}: unknown {entity_type} key {raw_key!r}")
            language_code = (
                row["language_code"].strip().lower().replace("_", "-").split("-", 1)[0]
            )
            name = row["name"].strip()
            if not language_code or not name:
                raise ValueError(f"Row {row_number}: language_code and name are required")
            identity = (model.__tablename__, entity.id, language_code, name)
            if identity in existing:
                skipped += 1
                continue
            session.add(
                model(**{relationship_name: entity}, language_code=language_code, name=name)
            )
            existing.add(identity)
            imported += 1

        await session.commit()
        return imported, skipped


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    imported, skipped = await import_rows(read_rows(args.csv_file))
    print(f"Imported {imported} localized names; skipped {skipped} existing names")


if __name__ == "__main__":
    asyncio.run(main())
