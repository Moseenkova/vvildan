import subprocess
import tempfile
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import Message

from bot.translation import translate_topic_audio

MAX_MEDIA_DURATION_SECONDS = 10 * 60
TRANSCRIBABLE_MEDIA_FIELDS = ("voice", "audio", "video", "video_note")
VIDEO_MEDIA_FIELDS = {"video", "video_note"}
SUPPORTED_AUDIO_SUFFIXES = {
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".ogg",
    ".wav",
    ".webm",
}
MIME_TYPE_SUFFIXES = {
    "audio/flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/x-wav": ".wav",
}


def get_transcribable_media(message: Message) -> tuple[str, Any] | None:
    for field in TRANSCRIBABLE_MEDIA_FIELDS:
        media = getattr(message, field, None)
        if media is not None:
            return field, media
    return None


def media_is_within_duration_limit(message: Message) -> bool:
    found = get_transcribable_media(message)
    return bool(found and found[1].duration <= MAX_MEDIA_DURATION_SECONDS)


def _media_suffix(kind: str, media: Any) -> str:
    if kind == "voice":
        return ".ogg"

    file_name = getattr(media, "file_name", None)
    suffix = Path(file_name).suffix.lower() if file_name else ""
    if kind in VIDEO_MEDIA_FIELDS:
        return suffix or ".mp4"
    if suffix in SUPPORTED_AUDIO_SUFFIXES:
        return suffix

    mime_type = getattr(media, "mime_type", None)
    if mime_type in MIME_TYPE_SUFFIXES:
        return MIME_TYPE_SUFFIXES[mime_type]

    return ".mp3"


def extract_audio_from_video(video_path: Path, audio_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-b:a",
            "64k",
            str(audio_path),
        ],
        check=True,
        timeout=120,
    )


async def transcribe_and_translate_media(
    message: Message,
    bot: Bot,
    topic_id: int,
    *,
    source_language: str,
    target_language: str,
    direction: str,
) -> tuple[str, str]:
    found = get_transcribable_media(message)
    if found is None:
        raise TypeError("Message does not contain transcribable media")

    kind, media = found
    with tempfile.TemporaryDirectory(prefix="support-media-") as temp_dir:
        source_path = Path(temp_dir) / f"source{_media_suffix(kind, media)}"
        await bot.download(media, destination=source_path)

        audio_path = source_path
        if kind in VIDEO_MEDIA_FIELDS:
            audio_path = Path(temp_dir) / "audio.mp3"
            extract_audio_from_video(source_path, audio_path)

        return await translate_topic_audio(
            topic_id,
            audio_path,
            source_language=source_language,
            target_language=target_language,
            direction=direction,
            caption=getattr(message, "caption", None),
        )
