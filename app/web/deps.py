from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.configs import settings
from app.core.security import verify_token
from app.db.models import UserRole
from app.db.session import SessionDep
from app.domain.auth_service import AuthService
from app.domain.chat_service import ChatService
from app.domain.info_service import InfoService
from app.web.schemas import CurrentUser


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_chat_service(session: SessionDep) -> ChatService:
    return ChatService(session)

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]

def get_info_service(session: SessionDep) -> InfoService:
    return InfoService(session)

InfoServiceDep = Annotated[InfoService, Depends(get_info_service)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(token: TokenDep) -> CurrentUser:
    payload = verify_token(token)
    if not payload or not payload.get("sub") or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return CurrentUser(
        user_id=payload.get("sub"),
        role=payload.get("role"),
        access_token=token
    )

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def require_admin(current_user: CurrentUserDep):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only administrator can perform this action")
    return current_user

AdminUserDep = Annotated[CurrentUser, Depends(require_admin)]