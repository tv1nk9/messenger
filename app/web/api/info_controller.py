from fastapi import APIRouter, Depends

from app.web.schemas import FindUsersResponse, FindUserRequest
from app.web.deps import CurrentUserDep, InfoServiceDep

router = APIRouter(prefix="/info", tags=["info"])

@router.post("/find_user", response_model=FindUsersResponse)
async def find_users(
    service: InfoServiceDep, cur_user: CurrentUserDep, req: FindUserRequest
):
    return await service.find_users(req)
