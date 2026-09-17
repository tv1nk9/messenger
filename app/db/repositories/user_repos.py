from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserModel


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_user(self, username: str, password_hash: str) -> str:
        """Create user and return new user uuid by str"""
        new_user = UserModel(username=username, password_hash=password_hash)
        self._session.add(new_user)
        await self._session.commit()
        await self._session.refresh(new_user)
        return str(new_user.id)

    async def get_user_by_id(self, user_id: str) -> UserModel | None:
        query = select(UserModel).where(UserModel.id == user_id)
        res = await self._session.execute(query)
        return res.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> UserModel | None:
        query = select(UserModel).where(UserModel.username == username)
        res = await self._session.execute(query)
        return res.scalar_one_or_none()

    async def delete_user(self):
        pass
