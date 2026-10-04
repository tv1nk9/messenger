from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ChatMemberRole,
    ChatModel,
    GroupChatMemberModel,
    GroupChatModel,
    MessageModel,
    PrivateChatModel,
)


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_user_chats(
            self, user_id: str
    ) -> list[ChatModel]:
        """ Возвращает список текущих чатов пользователя """

        # Собираем групповые чаты
        group_query = (
            select(GroupChatModel)
            .join(
                GroupChatMemberModel,
                GroupChatMemberModel.chat_id == GroupChatModel.chat_id,
            )
            .where(
                GroupChatMemberModel.user_id == user_id
            )
        )

        # Собираем личные чаты
        private_query = (
            select(PrivateChatModel)
            .options(
                # Загружаем участников чата сразу
                selectinload(PrivateChatModel.user_1),
                selectinload(PrivateChatModel.user_2),
            )
            .where(
                or_(
                    PrivateChatModel.user_1_id == user_id,
                    PrivateChatModel.user_2_id == user_id,
                )
            )
        )

        group_res = await self._session.scalars(group_query)
        private_res = await self._session.scalars(private_query)

        return list(group_res) + list(private_res)


    async def create_group_chat(
            self,
            name: str,
            description: str,
            cur_user_id: str
    ) -> str:

        new_chat = GroupChatModel(
            created_by=cur_user_id,
            chat_name=name,
            chat_desc=description,
        )

        member = GroupChatMemberModel(
            user_id=cur_user_id,
            role=ChatMemberRole.OWNER
        )
        new_chat.members.append(member)

        self._session.add(new_chat)
        await self._session.commit()

        return str(new_chat.chat_id)

    async def create_private_chat(
            self,
            cur_user_id: str,
            user_2_id: str
    ):
        us_1_id, us_2_id = sorted([cur_user_id, user_2_id])
        new_chat = PrivateChatModel(
            created_by=cur_user_id,
            user_1_id=us_1_id,
            user_2_id=us_2_id,
        )

        self._session.add(new_chat)
        await self._session.commit()

        return str(new_chat.chat_id)

    async def is_user_in_chat(self, user_id: str, chat_id: str) -> bool:
        """Проверяет, является ли пользователь участником чата (группа или приват)."""
        group_exists = await self._session.scalar(
            select(GroupChatMemberModel.chat_id)
            .where(
                GroupChatMemberModel.chat_id == chat_id,
                GroupChatMemberModel.user_id == user_id,
            )
            .limit(1)
        )
        if group_exists is not None:
            return True

        private_exists = await self._session.scalar(
            select(PrivateChatModel.chat_id)
            .where(
                PrivateChatModel.chat_id == chat_id,
                or_(
                    PrivateChatModel.user_1_id == user_id,
                    PrivateChatModel.user_2_id == user_id,
                ),
            )
            .limit(1)
        )
        return private_exists is not None

    async def get_private_chat_recipient_id(self, user_id: str, chat_id: str) -> str | None:
        """Для приватного чата возвращает id собеседника (recipient для сообщения)."""
        chat = await self._session.get(PrivateChatModel, chat_id)
        if chat is None:
            return None
        if str(chat.user_1_id) == str(user_id):
            return str(chat.user_2_id) if chat.user_2_id else None
        return str(chat.user_1_id) if chat.user_1_id else None

    async def create_message(
            self,
            chat_id: str,
            sender_id: str,
            recipient_id: str | None,
            content: str,
    ) -> MessageModel:
        message = MessageModel(
            chat_id=chat_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
        )
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def get_chat_history(self, chat_id: str, limit: int = 50) -> list[MessageModel]:
        res = await self._session.scalars(
            select(MessageModel)
            .where(MessageModel.chat_id == chat_id)
            .options(selectinload(MessageModel.sender))
            .order_by(MessageModel.created_at.desc(), MessageModel.id.desc())
            .limit(limit)
        )
        return list(res)[::-1]