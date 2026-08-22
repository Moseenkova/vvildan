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
    """Return conservative alternatives for composite municipality names."""
    values = [name]
    parenthetical = re.findall(r"\(([^)]+)\)", name)
    values.extend(parenthetical)
    values.append(re.sub(r"\s*\([^)]*\)\s*", " ", name))
    values.extend(part.strip() for part in name.split(","))

    result = []
    for value in values:
        value = value.strip()
        if value and value not in result:
            result.append(value)
    return result


def load_population_index(code: str, wanted_names: set[str]) -> dict[str, list]:
    """Find maximum populations only for names used by application cities."""
    from scripts.populate_location_names import CACHE_DIR, normalize, zip_rows

    index = defaultdict(list)
    for columns in zip_rows(CACHE_DIR / f"{code}.zip"):
        if len(columns) < 15 or columns[6] not in {"P", "A"}:
            continue
        population = int(columns[14] or 0)
        names = {columns[1], columns[2], *columns[3].split(",")}
        for name in names:
            normalized = normalize(name) if name else ""
            if normalized in wanted_names:
                index[normalized].append(
                    (
                        population,
                        float(columns[4]),
                        float(columns[5]),
                        columns[6],
                    )
                )
    return index


def choose_population(entries: list, airport_coordinates: list[tuple]) -> int:
    from scripts.populate_location_names import distance_km

    if not entries:
        return 0
    if airport_coordinates:
        ranked = [
            (
                min(
                    distance_km(latitude, longitude, airport_lat, airport_lon)
                    for airport_lat, airport_lon in airport_coordinates
                ),
                population,
                feature_class,
            )
            for population, latitude, longitude, feature_class in entries
        ]
        nearby = [entry for entry in ranked if entry[0] <= 100]
        if nearby:
            closest_distance = min(entry[0] for entry in nearby)
            nearby = [
                entry for entry in nearby if entry[0] <= closest_distance + 3
            ]
    else:
        nearby = []

    candidates = nearby or [
        (float("inf"), population, feature_class)
        for population, _, _, feature_class in entries
    ]
    populated_places = [
        entry for entry in candidates if entry[2] == "P" and entry[1] > 0
    ]
    populated_admins = [
        entry for entry in candidates if entry[2] == "A" and entry[1] > 0
    ]
    preferred = populated_places or populated_admins or candidates
    if airport_coordinates and nearby:
        return min(preferred, key=lambda entry: entry[0])[1]
    return max(entry[1] for entry in preferred)


async def populate(country_code: str | None, dry_run: bool) -> None:
    from scripts.populate_location_names import normalize
    from src.database import Airport, async_session_maker, City, Country, engine

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(City, Country.iso_code)
                .join(Country, City.country_id == Country.id)
                .order_by(City.id)
            )
        ).all()
        cities_by_country = defaultdict(list)
        airport_coordinates_by_city = defaultdict(list)
        airport_rows = await session.execute(
            select(Airport.city_id, Airport.latitude, Airport.longitude)
        )
        for city_id, latitude, longitude in airport_rows:
            airport_coordinates_by_city[city_id].append((latitude, longitude))
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
                entries = []
                for name in candidate_names(city.name):
                    entries.extend(
                        populations_by_name.get(normalize(name), [])
                    )
                if entries:
                    population = choose_population(
                        entries, airport_coordinates_by_city[city.id]
                    )
                    matched += 1
                else:
                    population = 0
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
