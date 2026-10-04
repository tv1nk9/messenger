from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GroupChatModel, PrivateChatModel
from app.db.repositories.chat_repos import ChatRepository
from app.db.repositories.user_repos import UserRepository
from app.web.schemas import (
    CurrentUser,
    FindUserRequest,
    FindUsersResponse,
    UserChatItem,
    UserChatsResponse,
    UserMessage,
)


class InfoService:
    def __init__(self, session: AsyncSession):
        self._user_repo = UserRepository(session)
        self._chat_repo = ChatRepository(session)

    async def find_users(
            self,find_users_req: FindUserRequest
    ) -> FindUsersResponse:

        user_info = find_users_req.query.split()
        if not user_info:
            return FindUsersResponse(users=None)

        try:
            users = await self._user_repo.get_users_by_filters(user_info=user_info)
        except Exception as e:
            logger.warning(f"Find users error: {e}")
            raise HTTPException(
                status_code=status.HTTP_418_IM_A_TEAPOT,
                detail="Find users failed"
            )

        response = {
            str(user.id): (user.name, user.surname, user.patronymic, user.email)
            for user in users
        }

        return FindUsersResponse(
            users=response
        )

    async def get_user_chats(
            self, cur_user: CurrentUser
    ) -> UserChatsResponse:
        try:
            chats = await self._chat_repo.get_user_chats(
                user_id=cur_user.user_id,
            )
        except Exception as e:
            logger.warning(f"Get user chats failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_418_IM_A_TEAPOT,
                detail="Get user chats failed"
            )

        response = []
        for chat in chats:
            if isinstance(chat, GroupChatModel):
                chat_name = chat.chat_name
            elif isinstance(chat, PrivateChatModel):
                # Название личного чата - это имя другого участника чата
                other_user = (
                    chat.user_2
                    if str(chat.user_1_id) == cur_user.user_id
                    else chat.user_1
                )
                if other_user is None:
                    chat_name = "Delete user"
                else:
                    chat_name = f"{other_user.name} {other_user.surname}"
            else:
                continue

            response.append(
                UserChatItem(
                    chat_id=str(chat.chat_id),
                    chat_name=chat_name,
                    last_message=None # ДОБАВИТЬ
                )
            )

        return UserChatsResponse(
            chats=response
        )


    async def get_chat_history(
            self, cur_user: CurrentUser, chat_id: str, limit: int = 50
    ) -> ChatHistoryResponse:
        """История сообщений чата. Доступна только участникам чата."""
        if not await self._chat_repo.is_user_in_chat(cur_user.user_id, chat_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this chat",
            )

        messages = await self._chat_repo.get_chat_history(chat_id, limit=limit)

        return ChatHistoryResponse(
            messages=[
                UserMessage(
                    user_id=str(m.sender_id),
                    username=(
                        f"{m.sender.name} {m.sender.surname}" if m.sender else "Deleted user"
                    ),
                    content=m.content,
                    created_at=m.created_at,
                )
                for m in messages
            ]
        )