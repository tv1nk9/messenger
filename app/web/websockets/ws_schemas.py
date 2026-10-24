from enum import Enum

from pydantic import BaseModel

class WsEvents(str, Enum):
    new_message = "new_message"
    chat_updated = "chat_updated"


class WsMessage(BaseModel):
    id: str
    chat_id: str
    user_id: str
    username: str | None
    content: str
    created_at: str


class WsChatUpdated(BaseModel):
    chat_id: str
    last_message: WsMessage
