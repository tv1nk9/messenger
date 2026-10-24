from enum import Enum

from pydantic import BaseModel, Field

from app.core.configs import chat_config


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


class SendMessage(BaseModel):
    chat_id: str
    user_id: str
    content: str = Field(min_length=1, max_length=chat_config.MAX_LENGTH_MESSAGE)
