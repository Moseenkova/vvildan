import asyncio
from functools import lru_cache
from pathlib import Path

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

# This lock protects direct OpenAI calls and response-chain updates in both directions.
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


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe a local audio file with the synchronous OpenAI client."""
    with audio_path.open("rb") as audio_file:
        transcription = get_openai_client().audio.transcriptions.create(
            model=get_settings().OPENAI_TRANSCRIPTION_MODEL,
            file=audio_file,
        )

    transcript = transcription.text.strip()
    if not transcript:
        raise RuntimeError("OpenAI returned an empty transcription")
    return transcript


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


async def translate_topic_audio(
    topic_id: int,
    audio_path: Path,
    *,
    source_language: str,
    target_language: str,
    direction: str,
    caption: str | None = None,
) -> tuple[str, str]:
    """Synchronously transcribe and translate one media message under the shared lock."""
    async with _translation_lock:
        topic = await get_customer_topic_by_topic_id(topic_id)
        if topic is None:
            raise LookupError(f"Customer topic {topic_id} was not found")

        transcript = transcribe_audio(audio_path)
        original_text = "\n\n".join(part for part in (caption, transcript) if part)
        translated, response_id = translate_text(
            original_text,
            source_language=source_language,
            target_language=target_language,
            direction=direction,
            previous_response_id=topic.last_openai_response_id,
        )
        updated = await update_customer_topic_response_id(topic_id, response_id)
        if not updated:
            raise LookupError(f"Customer topic {topic_id} was not found")
        return original_text, translated


def needs_translation(language_code: str | None) -> bool:
    return bool(language_code and language_code.split("-", 1)[0].lower() != "ru")
