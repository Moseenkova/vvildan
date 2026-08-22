#!/usr/bin/env python3
"""Fill missing airport-name localizations from Wikidata labels.

Airports are matched by ICAO (Wikidata P239), then IATA (P238). Existing
airport/language localizations are never replaced. Running repeatedly is safe.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
CACHE_FILE = PROJECT_ROOT / "data" / "wikidata" / "airport_labels.json"
SPARQL_URL = "https://query.wikidata.org/sparql"
API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "vvildan-airport-localizer/1.0 (airport localization importer)"
MAX_ATTEMPTS = 6
REQUEST_DELAY_SECONDS = 0.5
SPARQL_BATCH_SIZE = 100
ENTITY_BATCH_SIZE = 50


def supported_languages() -> set[str]:
    from scripts.populate_location_names import supported_languages as geonames_languages

    return geonames_languages()


def batches(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def fetch_json(url: str, params: dict[str, str]) -> dict:
    request_url = f"{url}?{urlencode(params)}"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = Request(
            request_url,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=120) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504}:
                raise
            caught_error = error
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        except (URLError, TimeoutError, ConnectionError) as error:
            caught_error = error
            delay = 2**attempt

        if attempt == MAX_ATTEMPTS:
            raise RuntimeError(
                f"Request failed after {MAX_ATTEMPTS} attempts: {url}"
            ) from caught_error
        delay = min(60.0, delay)
        print(f"Request failed; retrying in {delay:.1f}s", file=sys.stderr)
        time.sleep(delay)

    raise AssertionError("unreachable")


def sparql_entities(property_id: str, codes: set[str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    ordered_codes = sorted(codes)
    total_batches = (len(ordered_codes) + SPARQL_BATCH_SIZE - 1) // SPARQL_BATCH_SIZE
    for batch_number, code_batch in enumerate(
        batches(ordered_codes, SPARQL_BATCH_SIZE), start=1
    ):
        values = " ".join(json.dumps(code) for code in code_batch)
        query = f"""
            SELECT DISTINCT ?item ?code WHERE {{
              VALUES ?code {{ {values} }}
              ?item wdt:{property_id} ?code.
            }}
        """
        payload = fetch_json(SPARQL_URL, {"query": query, "format": "json"})
        for binding in payload["results"]["bindings"]:
            code = binding["code"]["value"].strip().upper()
            qid = binding["item"]["value"].rsplit("/", 1)[-1]
            result.setdefault(code, set()).add(qid)
        print(
            f"Wikidata {property_id}: batch {batch_number}/{total_batches}",
            file=sys.stderr,
        )
        time.sleep(REQUEST_DELAY_SECONDS)
    return result


def entity_labels(qids: set[str], languages: set[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    ordered_qids = sorted(qids, key=lambda value: int(value[1:]))
    total_batches = (len(ordered_qids) + ENTITY_BATCH_SIZE - 1) // ENTITY_BATCH_SIZE
    for batch_number, qid_batch in enumerate(
        batches(ordered_qids, ENTITY_BATCH_SIZE), start=1
    ):
        payload = fetch_json(
            API_URL,
            {
                "action": "wbgetentities",
                "ids": "|".join(qid_batch),
                "props": "labels",
                "languages": "|".join(sorted(languages)),
                "format": "json",
                "formatversion": "2",
            },
        )
        for qid, entity in payload.get("entities", {}).items():
            if entity.get("missing"):
                continue
            labels = {
                language.lower().split("-", 1)[0]: value["value"].strip()
                for language, value in entity.get("labels", {}).items()
                if value.get("value", "").strip()
            }
            result[qid] = labels
        print(
            f"Wikidata labels: batch {batch_number}/{total_batches}",
            file=sys.stderr,
        )
        time.sleep(REQUEST_DELAY_SECONDS)
    return result


def load_cache(languages: set[str], required_idents: set[str]) -> dict | None:
    if not CACHE_FILE.exists() or not CACHE_FILE.stat().st_size:
        return None
    payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    if set(payload.get("languages", [])) != languages:
        return None
    if not required_idents.issubset(set(payload.get("processed_idents", []))):
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
    from src.database import Airport, AirportName, async_session_maker, engine

    languages = supported_languages()
    async with async_session_maker() as session:
        airports = (await session.scalars(select(Airport).order_by(Airport.id))).all()
        existing = set(
            (
                await session.execute(
                    select(AirportName.airport_id, AirportName.language_code)
                )
            ).all()
        )
        missing_languages_by_airport = {
            airport.id: {
                language
                for language in languages
                if (airport.id, language) not in existing
            }
            for airport in airports
        }
        airports_to_lookup = [
            airport
            for airport in airports
            if missing_languages_by_airport[airport.id]
        ]
        required_idents = {airport.ident for airport in airports_to_lookup}

        if not airports_to_lookup:
            print(f"Database airports: {len(airports)}")
            print("Airports missing at least one localization: 0")
            print("Nothing to import")
            await engine.dispose()
            return

        cache = None if refresh else load_cache(languages, required_idents)
        if cache is None:
            iata_entities = await asyncio.to_thread(
                sparql_entities,
                "P238",
                {
                    airport.iata_code.upper()
                    for airport in airports_to_lookup
                    if airport.iata_code
                },
            )
            icao_entities = await asyncio.to_thread(
                sparql_entities,
                "P239",
                {
                    airport.icao_code.upper()
                    for airport in airports_to_lookup
                    if airport.icao_code
                },
            )

            qid_by_ident: dict[str, str] = {}
            ambiguous = 0
            conflicts = 0
            for airport in airports_to_lookup:
                icao_matches = icao_entities.get((airport.icao_code or "").upper(), set())
                iata_matches = iata_entities.get((airport.iata_code or "").upper(), set())
                qid = None
                if len(icao_matches) == 1:
                    qid = next(iter(icao_matches))
                    if len(iata_matches) == 1 and qid not in iata_matches:
                        conflicts += 1
                elif len(iata_matches) == 1:
                    qid = next(iter(iata_matches))
                elif icao_matches or iata_matches:
                    ambiguous += 1
                if qid:
                    qid_by_ident[airport.ident] = qid

            labels = await asyncio.to_thread(
                entity_labels, set(qid_by_ident.values()), languages
            )
            cache = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "languages": sorted(languages),
                "processed_idents": sorted(required_idents),
                "qid_by_ident": qid_by_ident,
                "labels": labels,
                "ambiguous_airports": ambiguous,
                "code_conflicts": conflicts,
            }
            save_cache(cache)
            print(f"Saved Wikidata cache to {CACHE_FILE}")
        else:
            print(f"Using Wikidata cache from {CACHE_FILE}")

        added = 0
        matched_airports = 0
        airports_with_new_names = set()
        qid_by_ident = cache["qid_by_ident"]
        labels_by_qid = cache["labels"]
        for airport in airports_to_lookup:
            qid = qid_by_ident.get(airport.ident)
            if not qid:
                continue
            matched_airports += 1
            for language, name in labels_by_qid.get(qid, {}).items():
                if language not in missing_languages_by_airport[airport.id]:
                    continue
                session.add(
                    AirportName(airport=airport, language_code=language, name=name)
                )
                existing.add((airport.id, language))
                airports_with_new_names.add(airport.id)
                added += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    print(f"Database airports: {len(airports)}")
    print(
        "Airports missing at least one localization: "
        f"{len(airports_to_lookup)}"
    )
    print(f"Matched to Wikidata: {matched_airports}")
    print(f"Airports with new names: {len(airports_with_new_names)}")
    print(f"Localized names added: {added}")
    print(f"Ambiguous code matches skipped: {cache.get('ambiguous_airports', 0)}")
    print(f"ICAO/IATA conflicts (ICAO preferred): {cache.get('code_conflicts', 0)}")
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
