from fastapi import APIRouter

from app.web.deps import ChatServiceDep, CurrentUserDep
from app.web.schemas import (
    GroupChatCreateRequest,
    GroupChatCreateResponse,
    PrivateChatCreateRequest,
    PrivateChatCreateResponse,
    SendMessage,
    UserMessage,
)

router = APIRouter(prefix="/chat", tags=["chats"])

@router.post("/create_group_chat", response_model=GroupChatCreateResponse)
async def create_group_chat(
        service: ChatServiceDep, cur_user: CurrentUserDep, req: GroupChatCreateRequest
):
    return await service.create_group_chat(
        new_chat_request=req,
        cur_user=cur_user
    )


@router.post("/create_private_chat", response_model=PrivateChatCreateResponse)
async def create_private_chat(
        service: ChatServiceDep, cur_user: CurrentUserDep, req: PrivateChatCreateRequest
):
    return await service.create_private_chat(
        new_chat_request=req,
        cur_user=cur_user
    )