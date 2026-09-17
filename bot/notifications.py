from datetime import date

CANDIDATE_NOTIFICATION_MESSAGES = {
    "en": {
        "headline": "A new candidate matches your request(s) {request_numbers}!",
        "candidate": "Candidate: {candidate_name}",
        "date": "Date: {dates}",
        "comment": "Comment: {comment}",
        "instruction": "Click Open matches to view the candidate in the web app.",
        "button": "Open matches",
        "any_date": "any date",
        "no_end_date": "no end date",
    },
    "ru": {
        "headline": ("Новый кандидат подходит для ваших запросов " "{request_numbers}!"),
        "candidate": "Кандидат: {candidate_name}",
        "date": "Дата: {dates}",
        "comment": "Комментарий: {comment}",
        "instruction": ("Нажмите «Открыть совпадения», чтобы увидеть " "кандидата в приложении."),
        "button": "Открыть совпадения",
        "any_date": "любая дата",
        "no_end_date": "без даты окончания",
    },
    "id": {
        "headline": "Kandidat baru cocok dengan permintaan Anda {request_numbers}!",
        "candidate": "Kandidat: {candidate_name}",
        "date": "Tanggal: {dates}",
        "comment": "Komentar: {comment}",
        "instruction": "Klik Buka kecocokan untuk melihat kandidat di aplikasi web.",
        "button": "Buka kecocokan",
        "any_date": "tanggal apa pun",
        "no_end_date": "tanpa tanggal akhir",
    },
}


def normalize_language(language_code: str | None) -> str:
    return (language_code or "en").lower().replace("_", "-").split("-", 1)[0]


def _format_date(value: date | None, language: str, fallback: str) -> str:
    if value is None:
        return fallback
    if language == "ru":
        return value.strftime("%d.%m.%Y")
    return value.isoformat()


def get_candidate_notification(
    language_code: str | None,
    *,
    request_numbers: str,
    candidate_name: str,
    departure: str,
    arrival: str,
    date_from: date | None,
    date_to: date | None,
    comment: str | None,
) -> tuple[str, str]:
    requested_language = normalize_language(language_code)
    language = requested_language if requested_language in CANDIDATE_NOTIFICATION_MESSAGES else "en"
    messages = CANDIDATE_NOTIFICATION_MESSAGES[language]
    if date_from == date_to:
        dates = _format_date(date_from or date_to, language, messages["any_date"])
    else:
        start = _format_date(date_from, language, messages["any_date"])
        end = _format_date(date_to, language, messages["no_end_date"])
        dates = f"{start} – {end}"

    lines = [
        messages["headline"].format(request_numbers=request_numbers),
        "",
        messages["candidate"].format(candidate_name=candidate_name),
        f"{departure} → {arrival}",
        messages["date"].format(dates=dates),
    ]
    if comment:
        lines.append(messages["comment"].format(comment=comment))
    lines.extend(("", messages["instruction"]))
    return "\n".join(lines), messages["button"]
