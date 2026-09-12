import logging
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from fastapi import HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import selectinload

from src.config import Settings, get_settings
from src.database import Conversation, Match, Message, Request, User, async_session_maker
from src.matches.service import _candidate_statement
from src.messages.schemas import (
    DialogMessagesSchema,
    DialogSchema,
    DialogUserSchema,
    MessageSchema,
    SendMatchMessageSchema,
)


def _message_schema(message: Message, user_id: int) -> MessageSchema:
    return MessageSchema(
        id=message.id,
        body=message.body,
        created_at=message.created_at,
        is_mine=message.sender_id == user_id,
        is_read=message.read_at is not None,
    )


def _other_user(conversation: Conversation, user_id: int) -> User:
    return conversation.user_two if conversation.user_one_id == user_id else conversation.user_one


def _dialog_options():
    return (
        selectinload(Conversation.user_one),
        selectinload(Conversation.user_two),
        selectinload(Conversation.messages),
    )


def _ensure_participant(conversation: Conversation | None, user_id: int) -> Conversation:
    if conversation is None or user_id not in (
        conversation.user_one_id,
        conversation.user_two_id,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found")
    return conversation


def _dialog_messages_schema(conversation: Conversation, user_id: int) -> DialogMessagesSchema:
    other = _other_user(conversation, user_id)
    messages = sorted(conversation.messages, key=lambda item: (item.created_at, item.id))
    return DialogMessagesSchema(
        id=conversation.id,
        other_user=DialogUserSchema(name=other.name, username=other.username),
        messages=[_message_schema(message, user_id) for message in messages],
    )


async def get_user_dialogs(user_id: int) -> list[DialogSchema]:
    async with async_session_maker() as session:
        conversations = (
            await session.scalars(
                select(Conversation)
                .where(
                    or_(
                        Conversation.user_one_id == user_id,
                        Conversation.user_two_id == user_id,
                    )
                )
                .options(*_dialog_options())
            )
        ).all()

        result = []
        for conversation in conversations:
            if not conversation.messages:
                continue
            latest = max(conversation.messages, key=lambda item: (item.created_at, item.id))
            unread_count = sum(
                message.sender_id != user_id and message.read_at is None
                for message in conversation.messages
            )
            other = _other_user(conversation, user_id)
            result.append(
                DialogSchema(
                    id=conversation.id,
                    other_user=DialogUserSchema(name=other.name, username=other.username),
                    latest_message=_message_schema(latest, user_id),
                    unread_count=unread_count,
                )
            )
        return sorted(
            result,
            key=lambda item: (item.latest_message.created_at, item.latest_message.id),
            reverse=True,
        )


async def get_dialog_messages(
    user_id: int, dialog_id: int, *, mark_read: bool
) -> DialogMessagesSchema:
    async with async_session_maker() as session:
        conversation = _ensure_participant(
            await session.scalar(
                select(Conversation).where(Conversation.id == dialog_id).options(*_dialog_options())
            ),
            user_id,
        )
        if mark_read:
            seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.execute(
                update(Message)
                .where(
                    Message.conversation_id == dialog_id,
                    Message.sender_id != user_id,
                    Message.read_at.is_(None),
                )
                .values(read_at=seen_at)
            )
            await session.commit()
            for message in conversation.messages:
                if message.sender_id != user_id and message.read_at is None:
                    message.read_at = seen_at
        return _dialog_messages_schema(conversation, user_id)


async def _load_conversation(session, dialog_id: int) -> Conversation | None:
    return await session.scalar(
        select(Conversation)
        .where(Conversation.id == dialog_id)
        .options(*_dialog_options())
        .execution_options(populate_existing=True)
    )


async def _append_message(session, conversation: Conversation, sender_id: int, body: str):
    message = Message(
        conversation=conversation,
        sender_id=sender_id,
        body=body.strip(),
    )
    session.add(message)
    await session.commit()
    return message


async def send_dialog_message(user_id: int, dialog_id: int, body: str) -> DialogMessagesSchema:
    body = body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    async with async_session_maker() as session:
        conversation = _ensure_participant(await _load_conversation(session, dialog_id), user_id)
        await _append_message(session, conversation, user_id, body)
        conversation = await _load_conversation(session, dialog_id)
        other = _other_user(conversation, user_id)
        sender = (
            conversation.user_one if conversation.user_one_id == user_id else conversation.user_two
        )
        result = _dialog_messages_schema(conversation, user_id)
    await notify_message_recipient(other, sender, dialog_id, body)
    return result


async def _requests_are_a_match(session, user_id: int, own: Request, matching: Request) -> bool:
    if own.user_id != user_id or matching.user_id == user_id:
        return False
    sender_id, courier_id = (
        (own.id, matching.id) if own.role.value == "sender" else (matching.id, own.id)
    )
    existing = await session.scalar(
        select(Match.id).where(
            Match.sender_request_id == sender_id,
            Match.courier_request_id == courier_id,
        )
    )
    if existing is not None:
        return True
    statement = _candidate_statement(own, user_id)
    if statement is None:
        return False
    candidate_id = await session.scalar(
        statement.where(Request.id == matching.id).with_only_columns(Request.id)
    )
    return candidate_id is not None


async def create_match_message(
    user_id: int, payload: SendMatchMessageSchema
) -> DialogMessagesSchema:
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    async with async_session_maker() as session:
        request_options = (
            selectinload(Request.user),
            selectinload(Request.departure_cities),
            selectinload(Request.arrival_cities),
        )
        own = await session.scalar(
            select(Request).where(Request.id == payload.own_request_id).options(*request_options)
        )
        matching = await session.scalar(
            select(Request)
            .where(Request.id == payload.matching_request_id)
            .options(*request_options)
        )
        if (
            own is None
            or matching is None
            or not await _requests_are_a_match(session, user_id, own, matching)
        ):
            raise HTTPException(status_code=404, detail="Matching candidate not found")

        one_id, two_id = sorted((user_id, matching.user_id))
        conversation = await session.scalar(
            select(Conversation).where(
                Conversation.user_one_id == one_id,
                Conversation.user_two_id == two_id,
            )
        )
        if conversation is None:
            conversation = Conversation(user_one_id=one_id, user_two_id=two_id)
            session.add(conversation)
            await session.flush()
        await _append_message(session, conversation, user_id, body)
        dialog_id = conversation.id
        conversation = await _load_conversation(session, dialog_id)
        sender = (
            conversation.user_one if conversation.user_one_id == user_id else conversation.user_two
        )
        result = _dialog_messages_schema(conversation, user_id)
    await notify_message_recipient(matching.user, sender, dialog_id, body)
    return result


def _dialog_webapp_url(settings: Settings, dialog_id: int) -> str:
    parts = urlsplit(settings.WEBAPP_URL)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({"tab": "messages", "dialog": str(dialog_id)})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


async def notify_message_recipient(
    recipient: User,
    sender: User,
    dialog_id: int,
    body: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open dialog",
                    web_app=WebAppInfo(url=_dialog_webapp_url(settings, dialog_id)),
                )
            ]
        ]
    )
    try:
        await bot.send_message(
            chat_id=recipient.tg_id,
            text=f"{sender.name} sent you a message:\n\n{body}",
            reply_markup=keyboard,
            parse_mode=None,
        )
    except Exception:
        logging.exception(
            "Could not notify Telegram user %s about dialog %s",
            recipient.tg_id,
            dialog_id,
        )
    finally:
        await bot.session.close()
