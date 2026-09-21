import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Uuid, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.configs import chat_config, user_config


class Base(DeclarativeBase):
    pass

class UserRole(enum.Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.USER, nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(user_config.MAX_LENGTH_USERNAME), unique=False, nullable=False
    )
    surname: Mapped[str] = mapped_column(
        String(user_config.MAX_LENGTH_USERNAME), unique=False, nullable=False
    )
    patronymic: Mapped[str] = mapped_column(
        String(user_config.MAX_LENGTH_USERNAME), unique=False, nullable=True
    )
    email: Mapped[str] = mapped_column(
        String(), unique=True, nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_moderator(self) -> bool:
        return self.role == UserRole.MODERATOR


class ChatModel(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_CHAT_NAME), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_CHAT_DESC),
        nullable=True,
        server_default=text("'Chat description...'"),
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    number_participants: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    messages = relationship(
        "MessageModel", cascade="all, delete-orphan", passive_deletes=True
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()")
    )
    chat_id: Mapped[str] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_MESSAGE), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
