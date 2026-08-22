#!/usr/bin/env python3
"""Download GeoNames aliases for app locations and fill localized-name tables.

GeoNames data is CC BY 4.0: https://www.geonames.org/
"""

import argparse
import asyncio
import csv
import io
import math
import re
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
CACHE_DIR = PROJECT_ROOT / "data" / "geonames"
BASE_URL = "https://download.geonames.org/export/dump"
LOCALES_FILE = PROJECT_ROOT / "frontend" / "src" / "i18n.js"
USER_AGENT = "vvildan-location-importer/1.0"
AIRPORT_FEATURE_CODES = {"AIRP", "AIRF"}
DOWNLOAD_DELAY_SECONDS = 1.0
MAX_DOWNLOAD_ATTEMPTS = 7
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
_last_download_started = 0.0


def supported_languages() -> set[str]:
    source = LOCALES_FILE.read_text(encoding="utf-8")
    match = re.search(r"const supportedLocales\s*=\s*\[(.*?)\]", source, re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not read supportedLocales from {LOCALES_FILE}")
    return set(re.findall(r"['\"]([a-zA-Z-]+)['\"]", match.group(1))) - {"en"}


def retry_delay(error: Exception, attempt: int) -> float:
    if isinstance(error, HTTPError):
        retry_after = error.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError):
                    pass
    return min(60.0, 2 ** (attempt - 1))


def download(url: str, destination: Path) -> Path:
    global _last_download_started
    if destination.exists() and destination.stat().st_size:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        since_last_request = time.monotonic() - _last_download_started
        if since_last_request < DOWNLOAD_DELAY_SECONDS:
            time.sleep(DOWNLOAD_DELAY_SECONDS - since_last_request)
        print(f"Downloading {url} (attempt {attempt}/{MAX_DOWNLOAD_ATTEMPTS})")
        request = Request(url, headers={"User-Agent": USER_AGENT})
        _last_download_started = time.monotonic()
        try:
            with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(destination)
            return destination
        except HTTPError as error:
            if error.code not in RETRYABLE_HTTP_STATUSES:
                raise
            caught_error = error
        except (URLError, TimeoutError, ConnectionError) as error:
            caught_error = error

        if attempt == MAX_DOWNLOAD_ATTEMPTS:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(
                f"Could not download {url} after {MAX_DOWNLOAD_ATTEMPTS} attempts"
            ) from caught_error
        delay = retry_delay(caught_error, attempt)
        print(f"Download failed: {caught_error}. Retrying in {delay:.1f} seconds")
        time.sleep(delay)

    raise AssertionError("unreachable")


def zip_rows(path: Path):
    with zipfile.ZipFile(path) as archive:
        files = [entry for entry in archive.infolist() if not entry.is_dir()]
        if not files:
            raise RuntimeError(f"Archive contains no files: {path}")
        # GeoNames archives can put a small README before the actual TSV file.
        # The location/alternate-name dataset is the largest member.
        data_file = max(files, key=lambda entry: entry.file_size)
        with archive.open(data_file) as raw:
            yield from csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")


def normalize(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 6371.0088 * 2 * math.asin(math.sqrt(value))


def country_geoname_ids() -> dict[str, int]:
    path = download(f"{BASE_URL}/countryInfo.txt", CACHE_DIR / "countryInfo.txt")
    result = {}
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) > 16 and columns[16]:
                result[columns[0]] = int(columns[16])
    return result


def load_country_features(code: str):
    path = download(f"{BASE_URL}/{code}.zip", CACHE_DIR / f"{code}.zip")
    cities_by_name = defaultdict(list)
    geo_airports = []
    for columns in zip_rows(path):
        if len(columns) < 15:
            continue
        geoname_id = int(columns[0])
        feature_class, feature_code = columns[6], columns[7]
        if feature_class == "P":
            names = {columns[1], columns[2], *columns[3].split(",")}
            population = int(columns[14] or 0)
            for name in names:
                if name:
                    cities_by_name[normalize(name)].append((population, geoname_id))
        elif feature_class == "S" and feature_code in AIRPORT_FEATURE_CODES:
            geo_airports.append(
                (geoname_id, float(columns[4]), float(columns[5]), columns[1])
            )
    return cities_by_name, geo_airports


def choose_airport_match(airport, candidates, radius_km: float):
    nearby = []
    for geoname_id, latitude, longitude, name in candidates:
        distance = distance_km(airport.latitude, airport.longitude, latitude, longitude)
        if distance <= radius_km:
            name_overlap = bool(
                set(normalize(airport.name).split()) & set(normalize(name).split())
            )
            nearby.append((not name_overlap, distance, geoname_id))
    return min(nearby)[2] if nearby else None


def load_best_aliases(code: str, languages: set[str], wanted_ids: set[int]):
    path = download(
        f"{BASE_URL}/alternatenames/{code}.zip",
        CACHE_DIR / "alternatenames" / f"{code}.zip",
    )
    best = {}
    for columns in zip_rows(path):
        if len(columns) < 8 or not columns[1].isdigit():
            continue
        geoname_id = int(columns[1])
        language = columns[2].lower().split("-", 1)[0]
        name = columns[3].strip()
        if geoname_id not in wanted_ids or language not in languages or not name:
            continue
        is_preferred = columns[4] == "1"
        is_short = columns[5] == "1"
        is_colloquial = columns[6] == "1"
        is_historic = columns[7] == "1"
        if is_historic:
            continue
        rank = (not is_preferred, is_colloquial, is_short, len(name))
        key = (geoname_id, language)
        if key not in best or rank < best[key][0]:
            best[key] = (rank, name)
    return {key: value[1] for key, value in best.items()}


async def populate(
    radius_km: float,
    dry_run: bool,
    country_code: str | None = None,
    language_code: str | None = None,
) -> None:
    from src.database import (
        Airport,
        AirportName,
        async_session_maker,
        City,
        CityName,
        Country,
        CountryName,
    )

    languages = supported_languages()
    if language_code:
        if language_code not in languages:
            raise ValueError(
                f"Unsupported language {language_code!r}; supported languages: "
                f"{', '.join(sorted(languages))}"
            )
        languages = {language_code}
    country_ids = country_geoname_ids()
    async with async_session_maker() as session:
        countries = (await session.scalars(select(Country))).all()
        cities = (await session.scalars(select(City))).all()
        airports = (await session.scalars(select(Airport))).all()
        cities_by_country = defaultdict(list)
        airports_by_country = defaultdict(list)
        country_by_id = {country.id: country for country in countries}
        city_by_id = {city.id: city for city in cities}
        for city in cities:
            cities_by_country[city.country_id].append(city)
        for airport in airports:
            airports_by_country[city_by_id[airport.city_id].country_id].append(airport)

        existing = set()
        for model, foreign_key in (
            (CountryName, "country_id"),
            (CityName, "city_id"),
            (AirportName, "airport_id"),
        ):
            rows = await session.execute(
                select(getattr(model, foreign_key), model.language_code, model.name)
            )
            existing.update((model, entity_id, lang, name) for entity_id, lang, name in rows)

        added = defaultdict(int)
        unmatched_cities = 0
        unmatched_airports = 0
        for country in countries:
            code = (country.iso_code or "").upper()
            if country_code and code != country_code:
                continue
            if len(code) != 2 or code not in country_ids:
                print(f"Skipping country without a GeoNames ISO mapping: {country.name}")
                continue
            print(f"Processing {code} ({country.name})")
            city_names, geo_airports = await asyncio.to_thread(load_country_features, code)
            entity_by_geoname_id = {country_ids[code]: (CountryName, country, "country")}

            for city in cities_by_country[country.id]:
                candidates = city_names.get(normalize(city.name), [])
                if not candidates:
                    unmatched_cities += 1
                    continue
                geoname_id = max(candidates)[1]
                entity_by_geoname_id[geoname_id] = (CityName, city, "city")

            for airport in airports_by_country[country.id]:
                geoname_id = choose_airport_match(airport, geo_airports, radius_km)
                if geoname_id is None:
                    unmatched_airports += 1
                    continue
                entity_by_geoname_id[geoname_id] = (AirportName, airport, "airport")

            aliases = await asyncio.to_thread(
                load_best_aliases, code, languages, set(entity_by_geoname_id)
            )
            for (geoname_id, language), name in aliases.items():
                model, entity, relationship = entity_by_geoname_id[geoname_id]
                identity = (model, entity.id, language, name)
                if identity in existing:
                    continue
                session.add(model(**{relationship: entity}, language_code=language, name=name))
                existing.add(identity)
                added[relationship] += 1
            if not dry_run:
                await session.commit()

        if dry_run:
            await session.rollback()
        print(
            f"Added country={added['country']}, city={added['city']}, "
            f"airport={added['airport']} localized names"
        )
        print(f"Unmatched cities={unmatched_cities}, airports={unmatched_airports}")
        if dry_run:
            print("Dry run: database changes were rolled back")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--airport-radius-km",
        type=float,
        default=15.0,
        help="Maximum distance for matching an app airport to GeoNames (default: 15)",
    )
    parser.add_argument(
        "--country",
        type=lambda value: value.strip().upper(),
        help="Process only one ISO 3166-1 alpha-2 country code (for example: RU)",
    )
    parser.add_argument(
        "--language",
        type=lambda value: value.strip().lower().replace("_", "-").split("-", 1)[0],
        help="Import only one supported language worldwide (for example: ru)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.country and (len(args.country) != 2 or not args.country.isalpha()):
        parser.error("--country must be a two-letter ISO country code (for example: RU)")
    await populate(
        args.airport_radius_km,
        args.dry_run,
        country_code=args.country,
        language_code=args.language,
    )


if __name__ == "__main__":
    asyncio.run(main())
