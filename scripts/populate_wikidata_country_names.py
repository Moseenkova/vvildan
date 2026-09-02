#!/usr/bin/env python3
"""Fill missing country-name localizations from Wikidata labels.

Countries are matched by ISO 3166-1 alpha-2 code (Wikidata P297). Existing
country/language localizations are never replaced. Running repeatedly is safe,
and countries without a Wikidata label remain untranslated.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
CACHE_FILE = PROJECT_ROOT / "data" / "wikidata" / "country_labels.json"


def load_cache(languages: set[str], required_codes: set[str]) -> dict | None:
    if not CACHE_FILE.exists() or not CACHE_FILE.stat().st_size:
        return None
    payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    if set(payload.get("languages", [])) != languages:
        return None
    if not required_codes.issubset(set(payload.get("processed_country_codes", []))):
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
    from scripts.populate_wikidata_airport_names import (
        entity_labels,
        sparql_entities,
        supported_languages,
    )
    from src.database import Country, CountryName, async_session_maker, engine

    languages = supported_languages()
    async with async_session_maker() as session:
        countries = (await session.scalars(select(Country).order_by(Country.id))).all()
        existing = set(
            (
                await session.execute(
                    select(CountryName.country_id, CountryName.language_code)
                )
            ).all()
        )
        missing_languages_by_country = {
            country.id: {
                language
                for language in languages
                if (country.id, language) not in existing
            }
            for country in countries
        }
        countries_to_lookup = [
            country
            for country in countries
            if missing_languages_by_country[country.id]
            and country.iso_code
            and len(country.iso_code) == 2
        ]
        required_codes = {country.iso_code.upper() for country in countries_to_lookup}

        if not countries_to_lookup:
            print(f"Database countries: {len(countries)}")
            print("Countries missing at least one localization: 0")
            print("Nothing to import")
            await engine.dispose()
            return

        cache = None if refresh else load_cache(languages, required_codes)
        if cache is None:
            entities_by_code = await asyncio.to_thread(
                sparql_entities, "P297", required_codes
            )
            qid_by_country_code: dict[str, str] = {}
            ambiguous = 0
            for code in required_codes:
                matches = entities_by_code.get(code, set())
                if len(matches) == 1:
                    qid_by_country_code[code] = next(iter(matches))
                elif matches:
                    ambiguous += 1

            labels = await asyncio.to_thread(
                entity_labels, set(qid_by_country_code.values()), languages
            )
            cache = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "languages": sorted(languages),
                "processed_country_codes": sorted(required_codes),
                "qid_by_country_code": qid_by_country_code,
                "labels": labels,
                "ambiguous_wikidata_matches": ambiguous,
            }
            save_cache(cache)
            print(f"Saved Wikidata cache to {CACHE_FILE}")
        else:
            print(f"Using Wikidata cache from {CACHE_FILE}")

        added = 0
        matched_countries = 0
        countries_with_new_names = set()
        qid_by_country_code = cache["qid_by_country_code"]
        labels_by_qid = cache["labels"]
        for country in countries_to_lookup:
            code = country.iso_code.upper()
            qid = qid_by_country_code.get(code)
            if not qid:
                continue
            matched_countries += 1
            for language, name in labels_by_qid.get(qid, {}).items():
                if language not in missing_languages_by_country[country.id]:
                    continue
                session.add(
                    CountryName(
                        country=country,
                        language_code=language,
                        name=name,
                    )
                )
                existing.add((country.id, language))
                countries_with_new_names.add(country.id)
                added += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    print(f"Database countries: {len(countries)}")
    print("Countries missing at least one localization: " f"{len(countries_to_lookup)}")
    print(f"Matched to Wikidata: {matched_countries}")
    print(f"Countries with new names: {len(countries_with_new_names)}")
    print(f"Localized names added: {added}")
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
