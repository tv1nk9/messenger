from sqlalchemy.ext.asyncio import AsyncSession


class ChatService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_group_chat(self):
        pass

    async def create_private_chat(self):
        pass

    async def add_user_to_chat(self):
        pass