import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import selectinload

from src.config import Settings, get_settings
from src.database import (
    City,
    CityName,
    CountryName,
    Match,
    RequestRole,
    RequestStatus,
    User,
    async_session_maker,
)
from src.database import Request as TravelRequest
from src.matches.schemas import MatchSchema, MatchUserSchema
from src.requests.schemas import RequestCitySchema, RequestSchema


def _match_relationships():
    return (
        selectinload(Match.sender_request).selectinload(TravelRequest.user),
        selectinload(Match.sender_request)
        .selectinload(TravelRequest.departure_cities)
        .selectinload(City.country),
        selectinload(Match.sender_request)
        .selectinload(TravelRequest.arrival_cities)
        .selectinload(City.country),
        selectinload(Match.courier_request).selectinload(TravelRequest.user),
        selectinload(Match.courier_request)
        .selectinload(TravelRequest.departure_cities)
        .selectinload(City.country),
        selectinload(Match.courier_request)
        .selectinload(TravelRequest.arrival_cities)
        .selectinload(City.country),
    )


def _candidate_statement(own: TravelRequest, user_id: int):
    departure_ids = [city.id for city in own.departure_cities]
    arrival_ids = [city.id for city in own.arrival_cities]
    if not departure_ids or not arrival_ids:
        return None

    if own.role == RequestRole.sender:
        opposite_role = RequestRole.courier
        date_condition = and_(
            *([TravelRequest.date_from >= own.date_from] if own.date_from is not None else []),
            *([TravelRequest.date_from <= own.date_to] if own.date_to is not None else []),
        )
    else:
        opposite_role = RequestRole.sender
        date_condition = and_(
            or_(
                TravelRequest.date_from.is_(None),
                TravelRequest.date_from <= own.date_from,
            ),
            or_(
                TravelRequest.date_to.is_(None),
                TravelRequest.date_to >= own.date_from,
            ),
        )

    return (
        select(TravelRequest)
        .where(
            TravelRequest.user_id != user_id,
            TravelRequest.role == opposite_role,
            TravelRequest.status == RequestStatus.active,
            TravelRequest.departure_cities.any(City.id.in_(departure_ids)),
            TravelRequest.arrival_cities.any(City.id.in_(arrival_ids)),
            date_condition,
        )
        .options(
            selectinload(TravelRequest.user),
            selectinload(TravelRequest.departure_cities).selectinload(City.country),
            selectinload(TravelRequest.arrival_cities).selectinload(City.country),
        )
        .order_by(TravelRequest.created_at.desc())
    )


async def _localized_requests(session, requests, language: str):
    language = language.lower().replace("_", "-").split("-", 1)[0]
    cities = {
        city.id: city
        for request in requests
        for city in request.departure_cities + request.arrival_cities
    }
    if not cities:
        return {request.id: RequestSchema.model_validate(request) for request in requests}

    country_by_city = dict(
        (await session.execute(select(City.id, City.country_id).where(City.id.in_(cities)))).all()
    )
    languages = {language, "en"}
    city_rows = (
        await session.execute(
            select(CityName.city_id, CityName.language_code, CityName.name).where(
                CityName.city_id.in_(cities), CityName.language_code.in_(languages)
            )
        )
    ).all()
    country_rows = (
        await session.execute(
            select(CountryName.country_id, CountryName.language_code, CountryName.name).where(
                CountryName.country_id.in_(set(country_by_city.values())),
                CountryName.language_code.in_(languages),
            )
        )
    ).all()

    def names_by_language(rows):
        names = {}
        for entity_id, language_code, name in rows:
            key = (entity_id, language_code)
            names[key] = min(name, names.get(key, name))
        return names

    city_names = names_by_language(city_rows)
    country_names = names_by_language(country_rows)

    def localized_city(city) -> RequestCitySchema:
        country_id = country_by_city[city.id]
        return RequestCitySchema.model_validate(city).model_copy(
            update={
                "name": city_names.get((city.id, language))
                or city_names.get((city.id, "en"))
                or city.name,
                "country_name": country_names.get((country_id, language))
                or country_names.get((country_id, "en"))
                or city.country.name,
            }
        )

    result = {}
    for request in requests:
        schema = RequestSchema.model_validate(request)
        result[request.id] = schema.model_copy(
            update={
                "departure_cities": [localized_city(city) for city in request.departure_cities],
                "arrival_cities": [localized_city(city) for city in request.arrival_cities],
            }
        )
    return result


async def get_user_matches(user_id: int, language: str = "en") -> list[MatchSchema]:
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        matches = (
            await session.scalars(
                select(Match)
                .where(
                    or_(
                        Match.sender_request.has(TravelRequest.user_id == user_id),
                        Match.courier_request.has(TravelRequest.user_id == user_id),
                    )
                )
                .options(*_match_relationships())
                .order_by(Match.created_at.desc())
            )
        ).all()
        own_requests = (
            await session.scalars(
                select(TravelRequest)
                .where(
                    TravelRequest.user_id == user_id,
                    TravelRequest.status == RequestStatus.active,
                )
                .options(
                    selectinload(TravelRequest.departure_cities).selectinload(City.country),
                    selectinload(TravelRequest.arrival_cities).selectinload(City.country),
                )
            )
        ).all()

        matched_pairs = {(match.sender_request_id, match.courier_request_id) for match in matches}
        candidates = []
        candidate_pair_keys = set()
        for own in own_requests:
            statement = _candidate_statement(own, user_id)
            if statement is None:
                continue
            rows = (await session.scalars(statement)).all()
            for candidate in rows:
                pair = (
                    (own.id, candidate.id)
                    if own.role == RequestRole.sender
                    else (candidate.id, own.id)
                )
                pair_key = (own.id, candidate.id)
                if pair in matched_pairs or pair_key in candidate_pair_keys:
                    continue
                candidate_pair_keys.add(pair_key)
                candidates.append((own, candidate))

        request_schemas = await _localized_requests(
            session,
            [
                request
                for match in matches
                for request in (match.sender_request, match.courier_request)
            ]
            + [request for pair in candidates for request in pair],
            language,
        )

        result = []
        for match in matches:
            is_sender = match.sender_request.user_id == user_id
            own = match.sender_request if is_sender else match.courier_request
            matching = match.courier_request if is_sender else match.sender_request
            seen_at = match.sender_seen_at if is_sender else match.courier_seen_at
            result.append(
                MatchSchema(
                    id=match.id,
                    status=match.status.value,
                    created_at=match.created_at,
                    is_new=seen_at is None,
                    is_candidate=False,
                    own_request=request_schemas[own.id],
                    matching_request=request_schemas[matching.id],
                    matching_user=MatchUserSchema(
                        name=matching.user.name,
                        username=matching.user.username,
                    ),
                )
            )
        for own, candidate in candidates:
            available_at = max(own.created_at, candidate.created_at)
            result.append(
                MatchSchema(
                    id=candidate.id,
                    status="proposed",
                    created_at=available_at,
                    is_new=user.matches_seen_at is None or available_at > user.matches_seen_at,
                    is_candidate=True,
                    own_request=request_schemas[own.id],
                    matching_request=request_schemas[candidate.id],
                    matching_user=MatchUserSchema(
                        name=candidate.user.name,
                        username=candidate.user.username,
                    ),
                )
            )
        return sorted(result, key=lambda item: item.created_at, reverse=True)


async def mark_user_matches_seen(user_id: int) -> None:
    seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
    async with async_session_maker() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(matches_seen_at=seen_at)
        )
        await session.execute(
            update(Match)
            .where(
                Match.sender_seen_at.is_(None),
                Match.sender_request.has(TravelRequest.user_id == user_id),
            )
            .values(sender_seen_at=seen_at)
        )
        await session.execute(
            update(Match)
            .where(
                Match.courier_seen_at.is_(None),
                Match.courier_request.has(TravelRequest.user_id == user_id),
            )
            .values(courier_seen_at=seen_at)
        )
        await session.commit()


def _request_summary(request: TravelRequest) -> str:
    departure = ", ".join(city.name for city in request.departure_cities)
    arrival = ", ".join(city.name for city in request.arrival_cities)
    if request.date_from == request.date_to:
        dates = str(request.date_from or request.date_to)
    else:
        dates = f"{request.date_from or 'any date'} – {request.date_to or 'no end date'}"
    comment = f"\nComment: {request.comment}" if request.comment else ""
    return f"{departure} → {arrival}\nDate: {dates}{comment}"


async def notify_request_candidates(
    request_id: int,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    async with async_session_maker() as session:
        request = await session.scalar(
            select(TravelRequest)
            .where(TravelRequest.id == request_id)
            .options(
                selectinload(TravelRequest.user),
                selectinload(TravelRequest.departure_cities).selectinload(City.country),
                selectinload(TravelRequest.arrival_cities).selectinload(City.country),
            )
        )
        if request is None:
            return
        statement = _candidate_statement(request, request.user_id)
        if statement is None:
            return
        candidates = (await session.scalars(statement)).all()

    requests_by_user = {}
    for candidate in candidates:
        requests_by_user.setdefault(candidate.user.tg_id, []).append(candidate)
    if not requests_by_user:
        return

    webapp_url = f"{settings.BASE_URL.rstrip('/')}/webapp/?tab=matches"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open matches", web_app=WebAppInfo(url=webapp_url))]
        ]
    )
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    try:
        for tg_id, matching_requests in requests_by_user.items():
            request_numbers = ", ".join(f"#{item.id}" for item in matching_requests)
            try:
                await bot.send_message(
                    chat_id=tg_id,
                    text=(
                        f"A new candidate matches your request(s) {request_numbers}!\n\n"
                        f"Candidate: {request.user.name}\n"
                        f"{_request_summary(request)}\n\n"
                        "Click Open matches to view the candidate in the web app."
                    ),
                    reply_markup=keyboard,
                    parse_mode=None,
                )
            except Exception:
                logging.exception(
                    "Could not notify Telegram user %s about request %s",
                    tg_id,
                    request_id,
                )
    finally:
        await bot.session.close()


async def notify_match_users(match_id: int, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    async with async_session_maker() as session:
        match = await session.scalar(
            select(Match).where(Match.id == match_id).options(*_match_relationships())
        )
        if match is None:
            return

    webapp_url = f"{settings.BASE_URL.rstrip('/')}/webapp/?tab=matches"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open matches", web_app=WebAppInfo(url=webapp_url))]
        ]
    )
    recipients = (
        (match.sender_request.user, match.sender_request, match.courier_request),
        (match.courier_request.user, match.courier_request, match.sender_request),
    )
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    try:
        delivered_to = set()
        for user, own_request, matching_request in recipients:
            if user.tg_id in delivered_to:
                continue
            delivered_to.add(user.tg_id)
            try:
                await bot.send_message(
                    chat_id=user.tg_id,
                    text=(
                        f"A new match was found for your request #{own_request.id}!\n\n"
                        f"Matched with: {matching_request.user.name}\n"
                        f"{_request_summary(matching_request)}\n\n"
                        "Click Open matches to view it in the web app."
                    ),
                    reply_markup=keyboard,
                    parse_mode=None,
                )
            except Exception:
                # One unreachable Telegram account must not prevent notifying
                # the other participant.
                logging.exception("Could not notify Telegram user %s", user.tg_id)
    finally:
        await bot.session.close()
