from fastapi import APIRouter

from app.web.deps import CurrentUserDep, InfoServiceDep
from app.web.schemas import FindUserRequest, FindUsersResponse, UserChatsResponse

router = APIRouter(prefix="/info", tags=["info"])

@router.post("/find_user", response_model=FindUsersResponse)
async def find_users(
    service: InfoServiceDep, cur_user: CurrentUserDep, req: FindUserRequest
):
    return await service.find_users(req)

@router.get("/user_chats", response_model=UserChatsResponse)
async def user_chats(
        service: InfoServiceDep, cur_user: CurrentUserDep
):
    return await service.get_user_chats(cur_user)