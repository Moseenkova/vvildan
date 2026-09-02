#!/usr/bin/env python3
"""Fill missing city-name localizations from Wikidata labels.

Cities are linked to Wikidata through their GeoNames ID (Wikidata P1566).
Existing city/language localizations are never replaced. Running repeatedly
is safe, and cities without a Wikidata label remain untranslated.
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
CACHE_FILE = PROJECT_ROOT / "data" / "wikidata" / "city_labels.json"


def city_key(country_code: str, city_name: str) -> str:
    return f"{country_code.upper()}|{city_name}"


def load_cache(languages: set[str], required_keys: set[str]) -> dict | None:
    if not CACHE_FILE.exists() or not CACHE_FILE.stat().st_size:
        return None
    payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    if set(payload.get("languages", [])) != languages:
        return None
    if not required_keys.issubset(set(payload.get("processed_city_keys", []))):
        return None
    return payload


def save_cache(payload: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_FILE.with_suffix(".json.part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(CACHE_FILE)


async def populate(dry_run: bool, refresh: bool) -> None:
    from scripts.populate_location_names import load_country_features, normalize
    from scripts.populate_wikidata_airport_names import (
        entity_labels,
        sparql_entities,
        supported_languages,
    )
    from src.database import City, CityName, Country, async_session_maker, engine

    languages = supported_languages()
    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(City, Country.iso_code)
                .join(Country, City.country_id == Country.id)
                .order_by(City.id)
            )
        ).all()
        cities = [row.City for row in rows]
        country_code_by_city_id = {
            row.City.id: (row.iso_code or "").upper() for row in rows
        }
        existing = set(
            (
                await session.execute(select(CityName.city_id, CityName.language_code))
            ).all()
        )
        missing_languages_by_city = {
            city.id: {
                language
                for language in languages
                if (city.id, language) not in existing
            }
            for city in cities
        }
        cities_to_lookup = [
            city for city in cities if missing_languages_by_city[city.id]
        ]
        required_keys = {
            city_key(country_code_by_city_id[city.id], city.name)
            for city in cities_to_lookup
        }

        if not cities_to_lookup:
            print(f"Database cities: {len(cities)}")
            print("Cities missing at least one localization: 0")
            print("Nothing to import")
            await engine.dispose()
            return

        cache = None if refresh else load_cache(languages, required_keys)
        if cache is None:
            cities_by_country: dict[str, list] = defaultdict(list)
            for city in cities_to_lookup:
                code = country_code_by_city_id[city.id]
                if len(code) == 2:
                    cities_by_country[code].append(city)

            geoname_id_by_city_key: dict[str, str] = {}
            unmatched_geonames = 0
            for code, country_cities in sorted(cities_by_country.items()):
                print(f"Matching cities in {code}", file=sys.stderr)
                geonames_cities, _ = await asyncio.to_thread(
                    load_country_features, code
                )
                for city in country_cities:
                    candidates = geonames_cities.get(normalize(city.name), [])
                    if not candidates:
                        unmatched_geonames += 1
                        continue
                    # Prefer the most populous exact-name match, as GeoNames import does.
                    geoname_id = max(candidates)[1]
                    key = city_key(code, city.name)
                    geoname_id_by_city_key[key] = str(geoname_id)

            entities_by_geoname_id = await asyncio.to_thread(
                sparql_entities, "P1566", set(geoname_id_by_city_key.values())
            )
            qid_by_city_key: dict[str, str] = {}
            ambiguous = 0
            for key, geoname_id in geoname_id_by_city_key.items():
                matches = entities_by_geoname_id.get(geoname_id, set())
                if len(matches) == 1:
                    qid_by_city_key[key] = next(iter(matches))
                elif matches:
                    ambiguous += 1

            labels = await asyncio.to_thread(
                entity_labels, set(qid_by_city_key.values()), languages
            )
            cache = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "languages": sorted(languages),
                "processed_city_keys": sorted(required_keys),
                "qid_by_city_key": qid_by_city_key,
                "labels": labels,
                "unmatched_geonames": unmatched_geonames,
                "ambiguous_wikidata_matches": ambiguous,
            }
            save_cache(cache)
            print(f"Saved Wikidata cache to {CACHE_FILE}")
        else:
            print(f"Using Wikidata cache from {CACHE_FILE}")

        added = 0
        matched_cities = 0
        cities_with_new_names = set()
        qid_by_city_key = cache["qid_by_city_key"]
        labels_by_qid = cache["labels"]
        for city in cities_to_lookup:
            key = city_key(country_code_by_city_id[city.id], city.name)
            qid = qid_by_city_key.get(key)
            if not qid:
                continue
            matched_cities += 1
            for language, name in labels_by_qid.get(qid, {}).items():
                if language not in missing_languages_by_city[city.id]:
                    continue
                session.add(CityName(city=city, language_code=language, name=name))
                existing.add((city.id, language))
                cities_with_new_names.add(city.id)
                added += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    print(f"Database cities: {len(cities)}")
    print(f"Cities missing at least one localization: {len(cities_to_lookup)}")
    print(f"Matched to Wikidata: {matched_cities}")
    print(f"Cities with new names: {len(cities_with_new_names)}")
    print(f"Localized names added: {added}")
    print(f"GeoNames matches not found: {cache.get('unmatched_geonames', 0)}")
    print(
        "Ambiguous Wikidata matches skipped: "
        f"{cache.get('ambiguous_wikidata_matches', 0)}"
    )
    if dry_run:
        print("Dry run: database changes were rolled back")
    await engine.dispose()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore the local Wikidata cache and download current data",
    )
    args = parser.parse_args()
    await populate(dry_run=args.dry_run, refresh=args.refresh)


if __name__ == "__main__":
    asyncio.run(main())
