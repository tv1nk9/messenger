import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError

from app.core.security import verify_token
from app.db.repositories.chat_repos import ChatRepository
from app.db.session import session_factory
from app.web.schemas import SendMessage
from app.web.websockets.conn_manager import manager

router = APIRouter(prefix="/ws", tags=["ws"])

async def _ws_auth(token: str | None) -> str | None:
    """Достаёт user_id из access-токена"""
    if not token:
        return None
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        return None

    return payload.get("sub")

@router.websocket("/chat/{chat_id}")
async def chat_ws(ws: WebSocket, chat_id: str, token: str = Query(...)):
    user_id = await _ws_auth(token)
    if not user_id:
        await ws.close(code=1008)
        return

    async with session_factory() as session:
        if not await ChatRepository(session).is_user_in_chat(user_id, chat_id):
            await ws.close(code=1008)
            return

    await manager.connect(ws, user_id=user_id, chat_id=chat_id)
    logger.info(f"WS connect: user={user_id} chat={chat_id}")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = SendMessage.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as e:
                await manager.send_personal(
                    chat_id=chat_id,
                    user_id=user_id,
                    message={"event": "error", "detail": f"Bad message: {e}"},
                )
                continue
            if data.chat_id != chat_id or data.user_id != user_id:
                await manager.send_personal(
                    chat_id=chat_id,
                    user_id=user_id,
                    message={"event": "error", "detail": "Forbidden"},
                )
                continue

            async with session_factory() as session:
                repo = ChatRepository(session)
                recipient_id = await repo.get_private_chat_recipient_id(user_id=user_id, chat_id=chat_id)
                message = await repo.create_message(
                    chat_id=chat_id,
                    sender_id=user_id,
                    recipient_id=recipient_id,
                    content=data.content,
                )

                payload = {
                    "event": "new_message",
                    "message": {
                        "id": str(message.id),
                        "chat_id": str(message.chat_id),
                        "user_id": str(message.sender_id),
                        "content": message.content,
                        "created_at": message.created_at.isoformat(),
                    },
                }

                await manager.broadcast_to_chat(chat_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(ws, user_id, chat_id)
        logger.info(f"WS disconnect: user={user_id}, chat={chat_id}")

