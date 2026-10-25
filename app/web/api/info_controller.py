from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.configs import settings
from app.web.deps import CurrentUserDep, InfoServiceDep
from app.web.schemas import (
    ChatHistoryResponse,
    FindUserRequest,
    FindUsersResponse,
    UserChatsResponse,
)

router = APIRouter(prefix="/info", tags=["info"])


@router.post("/find_user", response_model=FindUsersResponse)
async def find_users(
    service: InfoServiceDep, cur_user: CurrentUserDep, req: FindUserRequest
):
    return await service.find_users(req)


@router.get("/user_chats", response_model=UserChatsResponse)
async def user_chats(service: InfoServiceDep, cur_user: CurrentUserDep):
    return await service.get_user_chats(cur_user)


@router.get("/chat_history/{chat_id}", response_model=ChatHistoryResponse)
async def chat_history(
    chat_id: str,
    service: InfoServiceDep,
    cur_user: CurrentUserDep,
    limit: int = 50,
):
    return await service.get_chat_history(cur_user, chat_id, limit)
