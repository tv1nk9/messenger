from collections import defaultdict

from fastapi import WebSocket

# from app.web.schemas import UserMessage


class ConnectionManager:
    """
    Реестр активных WebSocket-подключений.

    Хранит:
      - user_to_ws:  chat_id -> {user_id: {WebSocket,...}} — сами соединения;
                     один пользователь может иметь несколько вкладок.
      - user_chats:  user_id -> {chat_id,...} — открытые чаты пользователя.
                     Нужно для мгновенных уведомлений: когда собеседник пишет
                     в чат, который у пользователя открыт в списке (но сам
                     чат не выбран), шлём ему событие chat_updated, и список
                     чатов обновляется без перезагрузки страницы.
    """
    def __init__(self):
        self.user_to_ws: dict[str, dict[str, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))
        self.user_chats: dict[str, set[str]] = defaultdict(set)

    async def connect(self, ws: WebSocket, user_id: str, chat_id: str):
        await ws.accept()
        self.user_to_ws[chat_id][user_id].add(ws)
        self.user_chats[user_id].add(chat_id)

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

        still_connected = ws in self.user_to_ws.get(chat_id, {}).get(user_id, ())
        if not still_connected:
            open_chats = self.user_chats.get(user_id)
            if open_chats:
                open_chats.discard(chat_id)
                if not open_chats:
                    del self.user_chats[user_id]

    async def send_personal(self, chat_id: str, user_id: str, message: dict):
        for ws in list(self.user_to_ws.get(chat_id, {}).get(user_id, ())):
            try:
                await ws.send_json(message)
            except RuntimeError:
                pass # соединение уже закрыто

    async def broadcast_to_chat(self, chat_id: str, message: dict):
        for uid in list(self.user_to_ws.get(chat_id, {})):
            await self.send_personal(chat_id, uid, message)

    async def notify_chat_updated(self, chat_id: str, sender_id: str, message: dict):
        """Шлём всем подключённым пользователям событие chat_updated.

        Так список чатов обновляется мгновенно: и превью последнего сообщения
        в уже известном чате, и появление нового чата. Фронт на это событие перезагружает список
        через REST; получателей, уже находящихся в этом чате, не пропускаем, они и так получат new_message.
        """
        payload = {
            "event": "chat_updated",
            "chat_id": str(chat_id),
            "last_message": message,
        }
        notified: set[str] = set()
        for cid, users in list(self.user_to_ws.items()):
            for uid in list(users):
                if str(uid) == str(sender_id) or uid in notified:
                    continue  # отправителю дублировать не нужно
                if str(cid) == str(chat_id):
                    continue  # эти участники получают new_message по этому чату
                notified.add(uid)
                await self.send_personal(cid, uid, payload)


manager = ConnectionManager()