import datetime
import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
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
        Enum(
            UserRole,
            name="user_role_enum",
            values_callable=lambda enum_cls: [item.value for item in enum_cls]
        ),
        default=UserRole.USER,
        nullable=False
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
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_moderator(self) -> bool:
        return self.role == UserRole.MODERATOR


class ChatType(enum.Enum):
    PRIVATE = "private"
    GROUP = "group"

class ChatModel(Base):
    __tablename__ = "chats"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    chat_type: Mapped[ChatType] = mapped_column(
        Enum(
            ChatType,
            name="chat_type_enum",
            values_callable=lambda enum_cls: [item.value for item in enum_cls]
        ),
        nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    __mapper_args__ = {
        "polymorphic_on": chat_type,
        "polymorphic_abstract": True
    }


class GroupChatModel(ChatModel):
    __tablename__ = "group_chats"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        primary_key=True
    )
    chat_name: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_CHAT_NAME),
        nullable=False
    )
    chat_desc: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_CHAT_DESC),
        nullable=True
    )

    members: Mapped[list["GroupChatMemberModel"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    __mapper_args__ = {
        "polymorphic_identity": ChatType.GROUP,
    }


class ChatMemberRole(enum.Enum):
    MEMBER = "member"
    OWNER = "owner"

class GroupChatMemberModel(Base):
    __tablename__ = "group_chat_members"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("group_chats.chat_id", ondelete="CASCADE"),
        primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    role: Mapped[ChatMemberRole] = mapped_column(
        Enum(
            ChatMemberRole,
            name="chat_member_role_enum",
            values_callable=lambda enum_cls: [item.value for item in enum_cls]
        ),
        default=ChatMemberRole.MEMBER,
        nullable=False
    )
    joined_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        nullable=False
    )

    user: Mapped["UserModel"] = relationship()
    chat: Mapped["GroupChatModel"] = relationship(
        back_populates="members"
    )


class PrivateChatModel(ChatModel):
    __tablename__ = 'private_chats'

    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        primary_key=True
    )
    # При удалении пользователя, история сообщений остается
    user_1_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    user_2_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    __mapper_args__ = {
        "polymorphic_identity": ChatType.PRIVATE,
    }

    # Перед сохранением нужно сортировать пользователей. Защита от создания двух личных чатов
    # (user_1_id, user_2_id = sorted([user_a_id, user_b_id])
    __table_args__ = (
        CheckConstraint(
            "user_1_id <> user_2_id",
            name="ck_private_chats_users_different",
        ),
        CheckConstraint(
            "user_1_id < user_2_id",
            name="ck_private_chats_users_ordered",
        ),
        UniqueConstraint(
            "user_1_id",
            "user_2_id",
            name="uq_private_chats_user_pair",
        ),
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False
    )
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    content: Mapped[str] = mapped_column(
        String(chat_config.MAX_LENGTH_MESSAGE),
        nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        nullable=False
    )

    chat: Mapped["ChatModel"] = relationship(
        back_populates="messages"
    )
    sender: Mapped["UserModel | None"] = relationship()

    __table_args__ = (
        Index(
            "ix_messages_chat_id_created_at_id",
            "chat_id",
            "created_at",
            "id",
        ),
    )
