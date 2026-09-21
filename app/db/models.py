from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.configs import chat_config, user_config


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()")
    )
    username: Mapped[str] = mapped_column(
        String(user_config.MAX_LENGTH_USERNAME), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ChatModel(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_CHAT_NAME), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_CHAT_NAME),
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
