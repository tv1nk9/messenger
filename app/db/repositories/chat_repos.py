from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ChatMemberRole,
    GroupChatMemberModel,
    GroupChatModel,
    PrivateChatModel,
)
from app.web.schemas import CurrentUser


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_group_chat(
            self,
            name: str,
            description: str,
            user: CurrentUser
    ) -> str:
        new_chat = GroupChatModel(
            created_by=user.user_id,
            chat_name=name,
            chat_desc=description,
        )

        member = GroupChatMemberModel(
            user_id=user.user_id,
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