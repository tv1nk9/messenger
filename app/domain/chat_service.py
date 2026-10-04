import datetime

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.chat_repos import ChatRepository
from app.web.schemas import (
    CurrentUser,
    GroupChatCreateRequest,
    GroupChatCreateResponse,
    PrivateChatCreateRequest,
    PrivateChatCreateResponse,
    SendMessage,
    UserMessage,
)


class ChatService:
    def __init__(self, session: AsyncSession):
        self._repo = ChatRepository(session)

    async def create_group_chat(
            self, new_chat_request: GroupChatCreateRequest, cur_user: CurrentUser
    ) -> GroupChatCreateResponse:
        try:
            new_chat_id = await self._repo.create_group_chat(
                name=new_chat_request.chat_name,
                description=new_chat_request.chat_description,
                cur_user_id=cur_user.user_id
            )
        except Exception as e:
            logger.warning(f"Group chat create error: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Group chat create failed"
            )

        return GroupChatCreateResponse(
            chat_id=new_chat_id
        )

    async def create_private_chat(
            self,
            new_chat_request: PrivateChatCreateRequest,
            cur_user: CurrentUser
    ):
        try:
            new_chat_id = await self._repo.create_private_chat(
                cur_user_id=cur_user.user_id,
                user_2_id=new_chat_request.user_2_id,
            )
        except Exception as e:
            logger.warning(f"Private chat create error: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Private chat create failed",
            )
        return PrivateChatCreateResponse(
            chat_id=new_chat_id
        )

    async def add_user_to_group_chat(self):
        pass

    async def get_messages(
            self, cur_user: CurrentUser
    ) -> list[UserMessage]:
        pass

    async def send_message(
            self,
            cur_user: CurrentUser,
            message: SendMessage,
    ) -> datetime.datetime:
        try:
            time = await self._repo.save_message(
                user_id=cur_user.user_id,
                chat_id=message.chat_id,
                content=message.content
            )
        except Exception:
            logger.warning(f"Send message failed: {f}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Send message failed"
            )

        return time