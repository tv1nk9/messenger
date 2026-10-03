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
)


class InfoService:
    def __init__(self, session: AsyncSession):
        self._user_repo = UserRepository(session)
        self._chat_repo = ChatRepository(session)

    async def find_users(
            self,find_users_req: FindUserRequest
    ) -> FindUsersResponse:
        try:
            users = await self._user_repo.get_users_by_filters(
                name=find_users_req.name,
                surname=find_users_req.surname,
                patronymic=find_users_req.patronymic
            )
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
                    if chat.user_1_id == cur_user.user_id
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