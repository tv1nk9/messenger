from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.configs import settings
from app.core.logger_config import setup_logger
from app.web.main import api_router

setup_logger()

app = FastAPI(
    title="Messenger",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
logger.info("App start")
