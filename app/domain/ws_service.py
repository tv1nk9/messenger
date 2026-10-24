from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MessageModel, UserModel
from app.db.repositories.chat_repos import ChatRepository
from app.db.repositories.user_repos import UserRepository


class WsService:
    def __init__(self, session: AsyncSession):
        self._chat_repo = ChatRepository(session)
        self._user_repo = UserRepository(session)

    async def is_user_in_chat(self, user_id: str, chat_id: str) -> bool:
        if not user_id or not chat_id:
            return False
        return await self._chat_repo.is_user_in_chat(user_id, chat_id)

    async def get_recipient_id(self, user_id: str, chat_id: str) -> str | None:
        if not user_id or not chat_id:
            return None
        return await self._chat_repo.get_private_chat_recipient_id(user_id, chat_id)

    async def create_message(
        self,
        chat_id: str,
        sender_id: str,
        recipient_id: str | None,
        content: str,
    ) -> MessageModel:
        return await self._chat_repo.create_message(
            chat_id, sender_id, recipient_id, content
        )

    async def get_user(self, user_id: str) -> UserModel | None:
        if not user_id:
            return None
        return await self._user_repo.get_user_by_id(user_id)
