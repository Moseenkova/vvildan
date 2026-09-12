#!/usr/bin/env python3
"""Update city populations from Wikidata population statements (P1082)."""

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
CACHE_FILE = PROJECT_ROOT / "data" / "wikidata" / "city_populations.json"
QUERY_BATCH_SIZE = 100
REQUEST_DELAY_SECONDS = 0.5


def city_key(country_code: str, city_name: str) -> str:
    return f"{country_code.upper()}|{city_name}"


def load_existing_city_qids() -> dict[str, str]:
    path = PROJECT_ROOT / "data" / "wikidata" / "city_labels.json"
    if not path.exists() or not path.stat().st_size:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("qid_by_city_key", {})


def find_geoname_ids(cities_by_country: dict[str, list]) -> dict[str, str]:
    from scripts.populate_city_populations import candidate_names
    from scripts.populate_location_names import load_country_features, normalize

    result = {}
    for code, cities in sorted(cities_by_country.items()):
        print(f"Matching cities in {code}", file=sys.stderr)
        geonames_cities, _ = load_country_features(code)
        for city in cities:
            candidates = []
            for name in candidate_names(city.name):
                candidates.extend(geonames_cities.get(normalize(name), []))
            if candidates:
                result[city_key(code, city.name)] = str(max(candidates)[1])
    return result


def fetch_population_statements(qids: set[str]) -> dict[str, int]:
    from scripts.populate_wikidata_airport_names import SPARQL_URL, batches, fetch_json

    statements = defaultdict(list)
    ordered_qids = sorted(qids, key=lambda value: int(value[1:]))
    total_batches = (len(ordered_qids) + QUERY_BATCH_SIZE - 1) // QUERY_BATCH_SIZE
    for number, qid_batch in enumerate(
        batches(ordered_qids, QUERY_BATCH_SIZE), start=1
    ):
        values = " ".join(f"wd:{qid}" for qid in qid_batch)
        query = f"""
            SELECT ?item ?population ?date ?rank WHERE {{
              VALUES ?item {{ {values} }}
              ?item p:P1082 ?statement.
              ?statement ps:P1082 ?population;
                         wikibase:rank ?rank.
              FILTER(?rank != wikibase:DeprecatedRank)
              OPTIONAL {{ ?statement pq:P585 ?date. }}
            }}
        """
        payload = fetch_json(SPARQL_URL, {"query": query, "format": "json"})
        for binding in payload["results"]["bindings"]:
            qid = binding["item"]["value"].rsplit("/", 1)[-1]
            population = int(float(binding["population"]["value"]))
            if population <= 0:
                continue
            rank = binding["rank"]["value"].rsplit("#", 1)[-1]
            rank_score = 1 if rank == "PreferredRank" else 0
            date = binding.get("date", {}).get("value", "")
            statements[qid].append((rank_score, date, population))
        print(f"Wikidata populations: batch {number}/{total_batches}", file=sys.stderr)
        time.sleep(REQUEST_DELAY_SECONDS)

    return {
        qid: max(values, key=lambda value: (value[0], value[1], value[2]))[2]
        for qid, values in statements.items()
    }


def load_cache(required_qids: set[str]) -> dict | None:
    if not CACHE_FILE.exists() or not CACHE_FILE.stat().st_size:
        return None
    payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    if not required_qids.issubset(set(payload.get("processed_qids", []))):
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
    from scripts.populate_wikidata_airport_names import sparql_entities
    from src.database import City, Country, async_session_maker, engine

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(City, Country.iso_code)
                .join(Country, City.country_id == Country.id)
                .order_by(City.id)
            )
        ).all()
        cities = [city for city, _ in rows]
        cities_by_country = defaultdict(list)
        code_by_city_id = {}
        for city, raw_code in rows:
            code = (raw_code or "").upper()
            if len(code) == 2:
                cities_by_country[code].append(city)
                code_by_city_id[city.id] = code

        if not cities:
            print("Database cities: 0")
            print("Nothing to import")
            await engine.dispose()
            return

        qid_by_key = load_existing_city_qids()
        missing_keys = {
            city_key(code_by_city_id[city.id], city.name)
            for city in cities
            if city.id in code_by_city_id
            and city_key(code_by_city_id[city.id], city.name) not in qid_by_key
        }
        if missing_keys:
            geoname_ids = await asyncio.to_thread(find_geoname_ids, cities_by_country)
            entities_by_geoname_id = await asyncio.to_thread(
                sparql_entities, "P1566", set(geoname_ids.values())
            )
            for key in missing_keys:
                geoname_id = geoname_ids.get(key)
                matches = entities_by_geoname_id.get(geoname_id or "", set())
                if len(matches) == 1:
                    qid_by_key[key] = next(iter(matches))

        required_qids = {
            qid_by_key[key]
            for city in cities
            if city.id in code_by_city_id
            for key in [city_key(code_by_city_id[city.id], city.name)]
            if key in qid_by_key
        }
        cache = None if refresh else load_cache(required_qids)
        if cache is None:
            populations = await asyncio.to_thread(
                fetch_population_statements, required_qids
            )
            cache = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "processed_qids": sorted(required_qids),
                "populations": populations,
            }
            save_cache(cache)
            print(f"Saved Wikidata cache to {CACHE_FILE}")
        else:
            print(f"Using Wikidata cache from {CACHE_FILE}")

        changed = 0
        populations = cache["populations"]
        matched_cities = 0
        for city in cities:
            code = code_by_city_id.get(city.id)
            if not code:
                continue
            qid = qid_by_key.get(city_key(code, city.name))
            if not qid:
                continue
            population = populations.get(qid)
            if population:
                matched_cities += 1
                if city.population != population:
                    city.population = population
                    changed += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    print(f"Database cities: {len(cities)}")
    print(f"Matched to a Wikidata population: {matched_cities}")
    print(f"Rows changed: {changed}")
    if dry_run:
        print("Dry run: database changes were rolled back")
    await engine.dispose()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore the local Wikidata population cache",
    )
    args = parser.parse_args()
    await populate(args.dry_run, args.refresh)


if __name__ == "__main__":
    asyncio.run(main())
