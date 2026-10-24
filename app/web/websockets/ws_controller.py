import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from loguru import logger
from pydantic import ValidationError

from app.core.security import get_user_id_from_access_token
from app.db.models import UserModel
from app.db.session import session_factory
from app.domain.ws_service import WsService
from app.web.websockets.conn_manager import manager
from app.web.websockets.ws_schemas import SendMessage, WsEvents, WsMessage

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/chat/{chat_id}")
async def chat_ws(ws: WebSocket, chat_id: str, token: str = Query(...)):
    user_id = get_user_id_from_access_token(token)
    if not user_id:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with session_factory() as session:
        service = WsService(session)
        if not await service.is_user_in_chat(user_id, chat_id):
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        recipient_id: str | None = await service.get_recipient_id(user_id, chat_id)
        sender: UserModel | None = await service.get_user(user_id)
        sender_name = f"{sender.name} {sender.surname}" if sender else None

    await manager.connect(ws, user_id=user_id, chat_id=chat_id)
    logger.info(f"WS connect: user={user_id} to chat={chat_id}")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = SendMessage.model_validate_json(raw)
            except (json.JSONDecodeError, ValidationError):
                continue
            if data.chat_id != chat_id or data.user_id != user_id:
                continue

            try:
                async with session_factory() as session:
                    service = WsService(session)
                    message = await service.create_message(
                        chat_id=chat_id,
                        sender_id=user_id,
                        recipient_id=recipient_id,
                        content=data.content,
                    )
                    payload = {
                        "event": WsEvents.new_message.value,
                        "message": WsMessage(
                            id=str(message.id),
                            chat_id=str(message.chat_id),
                            user_id=str(message.sender_id),
                            username=sender_name,
                            content=message.content,
                            created_at=message.created_at.isoformat(),
                        ).model_dump(),
                    }

                await manager.broadcast_to_chat(chat_id, payload)
                await manager.notify_chat_updated(
                    chat_id=chat_id, sender_id=user_id, message=payload["message"]
                )
            except Exception as e:
                logger.warning(
                    f"Failed to process message: {e} | User: '{user_id}' in chat: '{chat_id}'"
                )
                await manager.send_personal(
                    chat_id=chat_id,
                    user_id=user_id,
                    message={
                        "event": "error",
                        "detail": "Message not delivered. Please try again.",
                    },
                )

    except WebSocketDisconnect:
        manager.disconnect(ws, user_id, chat_id)
        logger.info(f"WS disconnect: user={user_id}, chat={chat_id}")
