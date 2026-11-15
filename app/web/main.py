from fastapi import APIRouter

from app.web.api import auth_controller, chat_controller, info_controller, analysis_controller
from app.web.websockets import ws_controller

api_router = APIRouter()

api_router.include_router(auth_controller.router)
api_router.include_router(chat_controller.router)
api_router.include_router(info_controller.router)
api_router.include_router(analysis_controller.router)
api_router.include_router(ws_controller.router)