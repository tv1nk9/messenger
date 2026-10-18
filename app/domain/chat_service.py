from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.chat_repos import ChatRepository
from app.db.repositories.user_repos import UserRepository
from app.web.schemas import (
    CurrentUser,
    GroupChatCreateRequest,
    GroupChatCreateResponse,
    PrivateChatCreateRequest,
    PrivateChatCreateResponse,
)


class ChatService:
    def __init__(self, session: AsyncSession):
        self._chat_repo = ChatRepository(session)
        self._user_repo = UserRepository(session)

    async def create_group_chat(
        self, new_chat_request: GroupChatCreateRequest, cur_user: CurrentUser
    ) -> GroupChatCreateResponse:
        try:
            new_chat_id = await self._chat_repo.create_group_chat(
                name=new_chat_request.chat_name,
                description=new_chat_request.chat_description,
                cur_user_id=cur_user.user_id,
            )
        except Exception as e:
            logger.warning(f"Group chat create error: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Group chat create failed"
            )

        return GroupChatCreateResponse(chat_id=new_chat_id)

    async def create_private_chat(
        self, new_chat_request: PrivateChatCreateRequest, cur_user: CurrentUser
    ):
        try:
            if not await self._user_repo.get_user_by_id(
                user_id=new_chat_request.user_2_id
            ):
                logger.info(f"User 2 with id: '{new_chat_request.user_2_id}' not found")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User 2 not found",
                )

            new_chat_id = await self._chat_repo.create_private_chat(
                cur_user_id=cur_user.user_id,
                user_2_id=new_chat_request.user_2_id,
            )
        except Exception as e:
            logger.warning(f"Private chat create error: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Private chat create failed",
            )
        return PrivateChatCreateResponse(chat_id=new_chat_id)

    async def add_user_to_group_chat(
        self,
        cur_user: CurrentUser,
        invited_user_id: str,
        chat_id: str,
    ) -> bool:
        try:
            if not await self._chat_repo.is_user_in_chat(
                user_id=cur_user.user_id, chat_id=chat_id
            ):
                logger.warning(f"User '{cur_user.user_id}' not in chat='{chat_id}'")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of this chat",
                )
            elif await self._chat_repo.is_user_in_chat(
                user_id=invited_user_id, chat_id=chat_id
            ):
                logger.warning(
                    f"Invited user='{invited_user_id}' already in chat='{chat_id}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Invited user already in chat",
                )

            await self._chat_repo.add_user_to_group_chat(
                chat_id=chat_id, invited_user_id=invited_user_id
            )

        except DBAPIError as e:
            logger.warning(f"User add chat failed. Error='{e}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed"
            )

        return True

    async def leave_group_chat(self):
        pass

    async def kick_user_from_group_chat(self):
        pass
