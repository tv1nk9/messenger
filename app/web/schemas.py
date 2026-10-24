from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.configs import chat_config, user_config
from app.db.models import UserRole


class CurrentUser(BaseModel):
    """Хранит информацию о текущем, авторизованном пользователе"""

    user_id: str
    role: UserRole
    access_token: str
    username: str | None = None


class UserMessage(BaseModel):
    user_id: str
    username: str
    content: str = Field(min_length=1, max_length=chat_config.MAX_LENGTH_MESSAGE)
    created_at: datetime


# Auth models
class UserRegisterRequest(BaseModel):
    role: UserRole
    name: str = Field(
        min_length=user_config.MIN_LENGTH_USERNAME,
        max_length=user_config.MAX_LENGTH_USERNAME,
    )
    surname: str = Field(
        min_length=user_config.MIN_LENGTH_USERNAME,
        max_length=user_config.MAX_LENGTH_USERNAME,
    )
    patronymic: str | None = Field(
        min_length=user_config.MIN_LENGTH_USERNAME,
        max_length=user_config.MAX_LENGTH_USERNAME,
    )
    email: EmailStr = Field(max_length=32)
    password: str = Field(
        min_length=user_config.MIN_LENGTH_PASSWORD,
        max_length=user_config.MAX_LENGTH_PASSWORD,
    )


class UserRegisterResponse(BaseModel):
    user_id: str | None


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# Chat models
class GroupChatCreateRequest(BaseModel):
    chat_name: str = Field(
        min_length=chat_config.MIN_LENGTH_CHAT_NAME,
        max_length=chat_config.MAX_LENGTH_CHAT_NAME,
    )
    chat_description: str | None = Field(
        default="Group Chat",
        min_length=chat_config.MIN_LENGTH_CHAT_DESC,
        max_length=chat_config.MAX_LENGTH_CHAT_DESC,
    )


class GroupChatCreateResponse(BaseModel):
    chat_id: str


class AddUserGroupChatRequest(BaseModel):
    user_id: str
    chat_id: str


class PrivateChatCreateRequest(BaseModel):
    user_2_id: str


class PrivateChatCreateResponse(BaseModel):
    chat_id: str


class ChatHistoryResponse(BaseModel):
    messages: list[UserMessage]


class UserChatItem(BaseModel):
    chat_id: str
    chat_name: str
    chat_type: str
    last_message: UserMessage | None = None
    # last_message_at: datetime.datetime | None


class UserChatsResponse(BaseModel):
    chats: list[UserChatItem]


class FindUserRequest(BaseModel):
    """Поиск пользователя по ФИО"""

    name: str
    offset: int | None = 0
    limit: int | None = 10


class FindUsersResponse(BaseModel):
    """{uuid: (Name, Surname, Patronymic | None)}"""

    users: dict[str, tuple[str, str, str | None, str]] | None
    has_more: bool
