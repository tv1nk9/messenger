import uuid
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    get_password_hash,
    verify_password,
    issue_tokens,
    verify_token,
)
from app.db.repositories.user_repos import UserRepository
from app.web.schemas import (
    UserRegisterRequest,
    UserLoginResponse,
    UserRegisterResponse,
    TokenRefreshRequest,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self._repo = UserRepository(session)

    async def registration(self, user_in: UserRegisterRequest) -> UserRegisterResponse:
        """raise HTTPException if user created failed | new user uuid by str if user created successful"""
        try:
            new_user_id = await self._repo.create_user(
                username=user_in.username,
                password_hash= await get_password_hash(user_in.password),
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exist",
            )

        return UserRegisterResponse(user_id=new_user_id)

    async def authorization(
        self, form_data: OAuth2PasswordRequestForm
    ) -> UserLoginResponse:
        user = await self._repo.get_user_by_username(form_data.username)
        if not user or not await verify_password(user.password_hash, form_data.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        ver = 1  # временно, потом редис добавлю
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())

        return self._get_tokens(user.id, ver, access_jti, refresh_jti)


    @staticmethod
    async def refresh_access_token(request: TokenRefreshRequest) -> UserLoginResponse:
        payload = verify_token(request.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        ver = 1 # временно, потом редис добавлю
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())

        return AuthService._get_tokens(user_id, ver, access_jti, refresh_jti)

    @staticmethod
    def _get_tokens(user_id: str, ver: int, access_jti: str, refresh_jti: str) -> UserLoginResponse:
        tokens = issue_tokens(user_id, ver, access_jti, refresh_jti)
        if (
            not tokens
            or not tokens.get("access_token")
            or not tokens.get("refresh_token")
        ):
            raise HTTPException(status_code=500, detail="Token generation failed")

        return UserLoginResponse(
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
        )
