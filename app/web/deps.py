from typing import Annotated

from fastapi import Depends, HTTPException, Query, status, Cookie
from fastapi.security import OAuth2PasswordBearer

from app.core.configs import settings
from app.core.security import verify_token
from app.db.models import UserModel
from app.db.session import SessionDep
from app.domain.auth_service import AuthService
from app.web.schemas import CurrentUser


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
# RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

TokenDep = Annotated[str, Depends(oauth2_scheme)]