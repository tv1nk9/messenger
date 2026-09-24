from pydantic import BaseModel, Field

from app.core.configs import chat_config, user_config
from app.db.models import UserRole


# Auxiliary models
class CurrentUser(BaseModel):
    user_id: str
    role: UserRole
    access_token: str
    username: str | None = None

class ChatInfo(BaseModel):
    chat_name: str
    chat_id: str
    created_by: str
    number_participants: str

class UserMessage(BaseModel):
    user_id: str
    username: str
    content: str = Field(min_length=1, max_length=chat_config.MAX_LENGTH_MESSAGE)
    created_at: str


# Request models
class UserRegisterRequest(BaseModel):
    role: UserRole
    name: str = Field(
        min_length=user_config.MIN_LENGTH_USERNAME,
        max_length=user_config.MAX_LENGTH_USERNAME
    )
    surname: str = Field(
        min_length=user_config.MIN_LENGTH_USERNAME,
        max_length=user_config.MAX_LENGTH_USERNAME
    )
    patronymic: str = Field(
        min_length=user_config.MIN_LENGTH_USERNAME,
        max_length=user_config.MAX_LENGTH_USERNAME
    )
    email: str = Field(
        min_length=4,
        max_length=32
    )
    password: str = Field(
        min_length=user_config.MIN_LENGTH_PASSWORD,
        max_length=user_config.MAX_LENGTH_PASSWORD
    )


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class GroupChatCreateRequest(BaseModel):
    chat_name: str = Field(
        min_length=chat_config.MIN_LENGTH_CHAT_NAME,
        max_length=chat_config.MAX_LENGTH_CHAT_NAME
    )
    chat_description: str = Field(
        min_length=chat_config.MIN_LENGTH_CHAT_DESC,
        max_length=chat_config.MAX_LENGTH_CHAT_DESC
    )
    created_at: str


class ChatConnectRequest(BaseModel):
    chat_name: str = Field(
        min_length=chat_config.MIN_LENGTH_CHAT_NAME,
        max_length=chat_config.MAX_LENGTH_CHAT_NAME
    )
    user_id: str


# Response models
class Message(BaseModel):
    message: str = Field(
        min_length=chat_config.MIN_LENGTH_MESSAGE,
        max_length=chat_config.MAX_LENGTH_MESSAGE
    )


class UserRegisterResponse(BaseModel):
    user_id: str | None


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


class RoomCreateResponse(BaseModel):
    room_id: str


class ListChatResponse(BaseModel):
    chats: list[ChatInfo]
