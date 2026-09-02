#!/usr/bin/env python3
"""Populate city populations from the cached GeoNames country datasets."""

import argparse
import asyncio
import re
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def candidate_names(name: str) -> list[str]:
    """Return city-name parts without treating districts as separate entities."""
    values = [name]
    values.append(re.sub(r"\s*\([^)]*\)\s*", " ", name))
    values.extend(re.findall(r"\(([^)]+)\)", name))
    values.extend(part.strip() for part in re.split(r"[,/]|\s*-\s*", name))

    result = []
    for value in values:
        value = value.strip()
        if value and value not in result:
            result.append(value)
    return result


def resolve_population(name: str, populations_by_name: dict[str, int]) -> int | None:
    """Resolve a city by its name, preferring the main name before qualifiers."""
    from scripts.populate_location_names import normalize

    exact = populations_by_name.get(normalize(name), 0)
    if exact > 0:
        return exact

    if "(" in name:
        main_name = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
        main_population = populations_by_name.get(normalize(main_name), 0)
        if main_population > 0:
            return main_population

    component_populations = [
        populations_by_name.get(normalize(part), 0)
        for part in re.split(r"[,/]|\s*-\s*|[()]", name)
        if part.strip()
    ]
    known_populations = [value for value in component_populations if value > 0]
    return max(known_populations) if known_populations else None


def load_population_index(code: str, wanted_names: set[str]) -> dict[str, int]:
    """Find populations of named cities, excluding administrative regions."""
    from scripts.populate_location_names import CACHE_DIR, normalize, zip_rows

    index = {}
    for columns in zip_rows(CACHE_DIR / f"{code}.zip"):
        if len(columns) < 15 or columns[6] != "P":
            continue
        population = int(columns[14] or 0)
        names = {columns[1], columns[2], *columns[3].split(",")}
        for name in names:
            normalized = normalize(name) if name else ""
            if normalized in wanted_names:
                index[normalized] = max(index.get(normalized, 0), population)
    return index


async def populate(country_code: str | None, dry_run: bool) -> None:
    from scripts.populate_location_names import normalize
    from src.database import City, Country, async_session_maker, engine

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(City, Country.iso_code)
                .join(Country, City.country_id == Country.id)
                .order_by(City.id)
            )
        ).all()
        cities_by_country = defaultdict(list)
        skipped_without_iso = []
        for city, raw_code in rows:
            code = (raw_code or "").upper()
            if country_code and code != country_code:
                continue
            if len(code) != 2:
                skipped_without_iso.append(city)
                continue
            cities_by_country[code].append(city)

        matched = 0
        unmatched = []
        changed = 0
        for code, cities in sorted(cities_by_country.items()):
            print(f"Processing {code}")
            wanted_names = {
                normalize(name)
                for city in cities
                for name in candidate_names(city.name)
            }
            populations_by_name = await asyncio.to_thread(
                load_population_index, code, wanted_names
            )
            for city in cities:
                population = resolve_population(city.name, populations_by_name)
                if population is not None:
                    matched += 1
                else:
                    # Preserve a value supplied later by another trusted source,
                    # such as Wikidata, when GeoNames has no city population.
                    population = city.population
                    unmatched.append(f"{code}|{city.name}")
                if city.population != population:
                    city.population = population
                    changed += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    print(f"Cities processed: {matched + len(unmatched)}")
    print(f"Matched to GeoNames: {matched}")
    print(f"Without a GeoNames match: {len(unmatched)}")
    print(f"Rows changed: {changed}")
    if skipped_without_iso:
        print(f"Skipped without ISO country code: {len(skipped_without_iso)}")
    if unmatched:
        print("Cities stored with population=0:")
        for key in unmatched:
            print(f"- {key}")
    if dry_run:
        print("Dry run: database changes were rolled back")
    await engine.dispose()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--country",
        type=lambda value: value.strip().upper(),
        help="Process only one ISO country code (for example: TR)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.country and (len(args.country) != 2 or not args.country.isalpha()):
        parser.error("--country must be a two-letter ISO country code")
    await populate(args.country, args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
