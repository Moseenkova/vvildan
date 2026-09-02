#!/usr/bin/env python3
"""Report airports that do not have a localized name for a language."""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import and_, func, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


async def report(language_code: str, summary_only: bool = False) -> None:
    from src.database import (
        Airport,
        AirportName,
        City,
        Country,
        async_session_maker,
        engine,
    )

    localized_name = (
        select(func.min(AirportName.name))
        .where(
            AirportName.airport_id == Airport.id,
            AirportName.language_code == language_code,
        )
        .correlate(Airport)
        .scalar_subquery()
    )

    async with async_session_maker() as session:
        total = await session.scalar(select(func.count()).select_from(Airport)) or 0
        localized = (
            await session.scalar(
                select(func.count(func.distinct(AirportName.airport_id))).where(
                    AirportName.language_code == language_code
                )
            )
            or 0
        )

        missing_rows = []
        if not summary_only:
            missing_rows = (
                await session.execute(
                    select(
                        Airport.ident,
                        Airport.name,
                        Airport.iata_code,
                        Airport.icao_code,
                        City.name.label("city_name"),
                        Country.name.label("country_name"),
                    )
                    .join(City, Airport.city_id == City.id)
                    .join(Country, City.country_id == Country.id)
                    .outerjoin(
                        AirportName,
                        and_(
                            AirportName.airport_id == Airport.id,
                            AirportName.language_code == language_code,
                        ),
                    )
                    .where(AirportName.id.is_(None), localized_name.is_(None))
                    .order_by(Country.name, City.name, Airport.name)
                )
            ).all()

    missing = total - localized
    print(f"Язык: {language_code}")
    print(f"Всего аэропортов: {total}")
    print(f"С локализацией: {localized}")
    print(f"Без локализации: {missing}")

    if summary_only:
        await engine.dispose()
        return

    print()

    if not missing_rows:
        print("All airports have localization.")
    else:
        print("Airports without localization:")
        for row in missing_rows:
            codes = "/".join(code for code in (row.iata_code, row.icao_code) if code)
            print(
                f"- {codes or row.ident}: {row.name} — "
                f"{row.city_name}, {row.country_name}"
            )

    await engine.dispose()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language",
        default="ru",
        type=lambda value: value.strip().lower().replace("_", "-").split("-", 1)[0],
        help="Language code to check (default: ru)",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print counts only, without listing missing airports",
    )
    args = parser.parse_args()
    if not args.language:
        parser.error("--language cannot be empty")
    await report(args.language, summary_only=args.summary_only)


if __name__ == "__main__":
    asyncio.run(main())
