from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.web.deps import AuthServiceDep, CurrentUserDep, AdminUserDep
from app.web.schemas import (
    Message,
    TokenRefreshRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRegisterResponse)
async def register(service: AuthServiceDep, admin_user: AdminUserDep, user_in: UserRegisterRequest):
    return await service.registration(user_in)

@router.post("/login", response_model=UserLoginResponse)
async def login(
        service: AuthServiceDep,
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    return await service.authorization(form_data)

@router.post("/refresh", response_model=UserLoginResponse)
async def refresh_access_token(
        service: AuthServiceDep, request: TokenRefreshRequest
):
    return await service.refresh_access_token(request)