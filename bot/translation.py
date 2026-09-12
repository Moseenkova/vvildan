import asyncio
from functools import lru_cache

from openai import OpenAI

from bot.utils import (
    get_customer_topic_by_topic_id,
    update_customer_topic_response_id,
)
from src.config import get_settings

TRANSLATION_INSTRUCTIONS = """You translate messages between a customer and
Russian-speaking support.
Translate only the message included in the current input into the requested target language.
Preserve meaning, tone, names, URLs, emoji, line breaks, and Telegram-style formatting.
Use earlier turns only to resolve context and ambiguity. Never answer the message or add commentary.
Return only the translated message."""

# One lock deliberately serializes both directions. The response ID is fetched while
# holding it, so every request continues from the response saved by the prior request.
_translation_lock = asyncio.Lock()


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    api_key = get_settings().OPENAI_API_KEY
    if api_key is None:
        raise RuntimeError("OPENAI_API_KEY is required to translate support messages")
    return OpenAI(api_key=api_key.get_secret_value())


def translate_text(
    text: str,
    *,
    source_language: str,
    target_language: str,
    direction: str,
    previous_response_id: str | None,
) -> tuple[str, str]:
    """Translate with the synchronous OpenAI client and return text plus response ID."""
    settings = get_settings()
    request = {
        "model": settings.OPENAI_TRANSLATION_MODEL,
        "instructions": TRANSLATION_INSTRUCTIONS,
        "input": (
            f"Direction: {direction}\n"
            f"Source language: {source_language}\n"
            f"Target language: {target_language}\n\n"
            f"Message:\n{text}"
        ),
    }
    if previous_response_id:
        request["previous_response_id"] = previous_response_id

    response = get_openai_client().responses.create(**request)
    translated = response.output_text.strip()
    if not translated:
        raise RuntimeError("OpenAI returned an empty translation")
    return translated, response.id


async def translate_topic_text(
    topic_id: int,
    text: str,
    *,
    source_language: str,
    target_language: str,
    direction: str,
) -> str:
    """Serialize translation calls and response-chain updates across all topics."""
    async with _translation_lock:
        topic = await get_customer_topic_by_topic_id(topic_id)
        if topic is None:
            raise LookupError(f"Customer topic {topic_id} was not found")

        translated, response_id = translate_text(
            text,
            source_language=source_language,
            target_language=target_language,
            direction=direction,
            previous_response_id=topic.last_openai_response_id,
        )
        updated = await update_customer_topic_response_id(topic_id, response_id)
        if not updated:
            raise LookupError(f"Customer topic {topic_id} was not found")
        return translated


def needs_translation(language_code: str | None) -> bool:
    return bool(language_code and language_code.split("-", 1)[0].lower() != "ru")
