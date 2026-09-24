from fastapi import APIRouter

from app.web.deps import CurrentUserDep
from app.web.schemas import GroupChatCreateRequest

router = APIRouter(prefix="/chat", tags=["chats"])

@router.post("/create_group_chat", response_model=GroupChatCreateResponse)
async def create_group_chat(
        service: ChatServiceDep, cur_user: CurrentUserDep, req: GroupChatCreateRequest
):
    pass

@router.post("/create_private_chat", response_model=PrivateChatCreateResponse)
async def create_private_chat(
        service: ChatServiceDep, cur_user: CurrentUserDep, req: PrivateChatCreateRequest
):
    pass