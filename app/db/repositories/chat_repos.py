from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ChatMemberRole,
    ChatModel,
    GroupChatMemberModel,
    GroupChatModel,
    PrivateChatModel,
)


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_user_chats(
            self, user_id: str
    ) -> list[ChatModel]:
        """ Возвращает список текущих чатов пользователя """

        # Собираем групповые чаты в которых состоит пользователь
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

        # Собираем личные чаты в которых состоит пользователь
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