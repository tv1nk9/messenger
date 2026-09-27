from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.db.repositories.user_repos import UserRepository
from app.web.schemas import FindUserRequest, FindUsersResponse


class InfoService:
    def __init__(self, session: AsyncSession):
        self._repo = UserRepository(session)

    async def find_users(
            self,
            find_users_req: FindUserRequest
    ) -> FindUsersResponse:
        try:
            users = await self._repo.get_users_by_filters(
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
            str(user.id): (user.name, user.surname, user.patronymic)
            for user in users
        }

        return FindUsersResponse(
            users=response
        )