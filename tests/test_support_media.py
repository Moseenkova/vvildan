from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select

import bot.media as media
import bot.translation as translation
from bot.utils import create_customer_tg_topic
from src.database import CustomerTgTopic, async_session_maker


def test_extract_audio_from_video_uses_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    run = Mock()
    monkeypatch.setattr(media.subprocess, "run", run)
    video_path = tmp_path / "message.mp4"
    audio_path = tmp_path / "audio.mp3"

    media.extract_audio_from_video(video_path, audio_path)

    command = run.call_args.args[0]
    assert command[0] == "ffmpeg"
    assert "-vn" in command
    assert str(video_path) in command
    assert command[-1] == str(audio_path)
    assert run.call_args.kwargs == {"check": True, "timeout": 120}


@pytest.mark.asyncio
async def test_video_is_downloaded_extracted_and_translated(monkeypatch) -> None:
    video = SimpleNamespace(duration=60, file_name="clip.mp4", mime_type="video/mp4")
    message = SimpleNamespace(video=video, caption="caption")
    bot = SimpleNamespace(download=AsyncMock())
    extract = Mock()
    translate = AsyncMock(return_value=("original", "translated"))
    monkeypatch.setattr(media, "extract_audio_from_video", extract)
    monkeypatch.setattr(media, "translate_topic_audio", translate)

    result = await media.transcribe_and_translate_media(
        message,
        bot,
        456,
        source_language="id",
        target_language="ru",
        direction="customer to support",
    )

    assert result == ("original", "translated")
    bot.download.assert_awaited_once()
    downloaded_path = bot.download.await_args.kwargs["destination"]
    assert downloaded_path.suffix == ".mp4"
    extracted_path = extract.call_args.args[1]
    assert extracted_path.name == "audio.mp3"
    translate.assert_awaited_once_with(
        456,
        extracted_path,
        source_language="id",
        target_language="ru",
        direction="customer to support",
        caption="caption",
    )


@pytest.mark.asyncio
async def test_audio_translation_continues_and_saves_response_id(
    database, monkeypatch, tmp_path: Path
) -> None:
    await create_customer_tg_topic(123, 456, "id")
    transcribe = Mock(return_value="Pesan suara")
    translate = Mock(return_value=("Голосовое сообщение", "response-audio"))
    monkeypatch.setattr(translation, "transcribe_audio", transcribe)
    monkeypatch.setattr(translation, "translate_text", translate)
    audio_path = tmp_path / "voice.ogg"

    result = await translation.translate_topic_audio(
        456,
        audio_path,
        source_language="id",
        target_language="ru",
        direction="customer to support",
    )

    assert result == ("Pesan suara", "Голосовое сообщение")
    transcribe.assert_called_once_with(audio_path)
    translate.assert_called_once_with(
        "Pesan suara",
        source_language="id",
        target_language="ru",
        direction="customer to support",
        previous_response_id=None,
    )
    async with async_session_maker() as session:
        topic = await session.scalar(select(CustomerTgTopic))
    assert topic is not None
    assert topic.last_openai_response_id == "response-audio"
