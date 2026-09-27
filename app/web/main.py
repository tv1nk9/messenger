from fastapi import APIRouter

from app.web.api import auth_controller, chat_controller, info_controller

api_router = APIRouter()

api_router.include_router(auth_controller.router)
api_router.include_router(chat_controller.router)
api_router.include_router(info_controller.router)