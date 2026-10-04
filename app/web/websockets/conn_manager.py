from collections import defaultdict

from fastapi import WebSocket

# from app.web.schemas import UserMessage


class ConnectionManager:
    """
    Реестр активных WebSocket-подключений.

    Хранит:
      - user_to_ws:    chat_id -> {user_id: {WebSocket,...}} — сами соединения;
                       один пользователь может иметь несколько вкладок.
    Рассылка идёт строго по составу конкретного чата (chat_id), поэтому
    приватные чаты с одинаковым набором двух пользователей не "смешиваются".
    """
    def __init__(self):
        self.user_to_ws: dict[str, dict[str, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))

    async def connect(self, ws: WebSocket, user_id: str, chat_id: str):
        await ws.accept()
        self.user_to_ws[chat_id][user_id].add(websockets)

    def disconnect(self, ws: WebSocket, user_id: str, chat_id: str):
        chats = self.user_to_ws.get(chat_id)
        if not chats:
            return
        sockets = chats.get(user_id)
        if sockets:
            sockets.discard(ws)
            if not sockets:
                del chats[user_id]
        if not chats:
            del self.user_to_ws[chat_id]

    async def send_personal(self, chat_id: str, user_id: str, message: dict):
        for ws in list(self.user_to_ws.get(chat_id, {}).get(user_id, ())):
            try:
                await ws.send_json(message)
            except RuntimeError:
                pass # соединение уже закрыто

    async def broadcast_to_chat(self, chat_id: str, message: dict):
        for uid in list(self.user_to_ws.get(chat_id, {})):
            await self.send_personal(chat_id, uid, message)


manager = ConnectionManager()