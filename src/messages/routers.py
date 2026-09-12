from fastapi import APIRouter, Depends

from src.auth.deps import get_current_user
from src.messages.schemas import (
    DialogMessagesSchema,
    DialogSchema,
    SendMatchMessageSchema,
    SendMessageSchema,
)
from src.messages.service import (
    create_match_message,
    get_dialog_messages,
    get_user_dialogs,
    send_dialog_message,
)

messages_router = APIRouter(prefix="/api/messages", tags=["Messages"])


@messages_router.get("", response_model=list[DialogSchema])
async def get_my_dialogs(user=Depends(get_current_user)):
    return await get_user_dialogs(user.id)


@messages_router.post("/from-match", response_model=DialogMessagesSchema, status_code=201)
async def message_matching_candidate(
    payload: SendMatchMessageSchema,
    user=Depends(get_current_user),
):
    return await create_match_message(user.id, payload)


@messages_router.get("/{dialog_id}", response_model=DialogMessagesSchema)
async def get_dialog(dialog_id: int, user=Depends(get_current_user)):
    return await get_dialog_messages(user.id, dialog_id, mark_read=True)


@messages_router.post("/{dialog_id}", response_model=DialogMessagesSchema)
async def reply_to_dialog(
    dialog_id: int,
    payload: SendMessageSchema,
    user=Depends(get_current_user),
):
    return await send_dialog_message(user.id, dialog_id, payload.body)
