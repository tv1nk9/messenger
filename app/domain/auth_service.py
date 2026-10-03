import uuid

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    get_password_hash,
    issue_tokens,
    verify_password,
    verify_token,
)
from app.db.models import UserRole
from app.db.repositories.user_repos import UserRepository
from app.web.schemas import (
    TokenRefreshRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self._repo = UserRepository(session)

    async def registration(self, user_in: UserRegisterRequest) -> UserRegisterResponse:
        """raise HTTPException if user created failed | new user uuid by str if user created successful"""
        try:
            new_user_id = await self._repo.create_user(
                role=user_in.role,
                name=user_in.name,
                surname=user_in.surname,
                patronymic=user_in.patronymic,
                email=user_in.email,
                password_hash= await get_password_hash(user_in.password),
            )
        except IntegrityError:
            logger.warning(f"Registration failed. Email '{user_in.email}' already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exist",
            )

        return UserRegisterResponse(user_id=new_user_id)

    async def authorization(
        self, form_data: OAuth2PasswordRequestForm
    ) -> UserLoginResponse:
        user = await self._repo.get_user_by_email(form_data.username) # form_data.username это email пользователя
        if not user or not await verify_password(user.password_hash, form_data.password):
            logger.warning(f"Authorization failed for user email: '{form_data.username}'. Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        ver = 1  # временно
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())

        return self._get_tokens(str(user.id), user.role, ver, access_jti, refresh_jti)

    @staticmethod
    async def refresh_access_token(request: TokenRefreshRequest) -> UserLoginResponse:
        payload = verify_token(request.refresh_token)
        if not payload or payload.get("type") != "refresh":
            logger.warning("Invalid or expired refresh token")
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Invalid token payload")
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user_role = payload.get("role")

        ver = 1 # временно
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())

        return AuthService._get_tokens(user_id, user_role, ver, access_jti, refresh_jti)

    @staticmethod
    def _get_tokens(user_id: str, role: UserRole, ver: int, access_jti: str, refresh_jti: str) -> UserLoginResponse:
        tokens = issue_tokens(user_id, role, ver, access_jti, refresh_jti)
        if (
            not tokens
            or not tokens.get("access_token")
            or not tokens.get("refresh_token")
        ):
            logger.warning(f"Token generation failed for user with id: '{user_id}'")
            raise HTTPException(status_code=500, detail="Token generation failed")

        return UserLoginResponse(
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
        )
