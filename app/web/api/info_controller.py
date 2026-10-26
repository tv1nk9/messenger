from typing import Optional

from fastapi import APIRouter, Query

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
    limit: int = Query(default=50, le=100),
    cursor: Optional[str | None] = Query(default=None),
):
    if isinstance(cursor, str) and cursor.lower() in ("null", "none", ""):
        cursor = None
    return await service.get_chat_history(cur_user, chat_id, limit, cursor)
