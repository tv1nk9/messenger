from contextlib import asynccontextmanager
from loguru import logger

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import redis.asyncio as aioredis

from app.core.configs import settings
from app.core.logger_config import setup_logger
from app.db.redis_client import build_redis_client
from app.web.main import api_router

setup_logger()


def create_app(redis_client: aioredis.Redis | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(fa_app: FastAPI):
        client = redis_client or build_redis_client()
        fa_app.state.redis = client

        try:
            await client.ping()
            logger.info("Redis is available")
        except Exception as e:
            logger.info(f"Redis is not available | Error: {e}")

        yield

        if redis_client is None:
            await client.aclose()

    new_app = FastAPI(
        title="Messenger",
        lifespan=lifespan,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    new_app.add_middleware(
        GZipMiddleware,
        minimum_size=settings.GZIP_SIZE,
    )
    new_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

    new_app.mount("/static", StaticFiles(directory="static"), name="static")

    new_app.include_router(api_router, prefix=settings.API_V1_STR)

    return new_app

app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/login_page", response_class=HTMLResponse, summary="Auth page")
async def get_auth_page(request: Request):
    return settings.templates.TemplateResponse(request, "auth.html")


@app.get("/", response_class=HTMLResponse, summary="Chats page")
async def main_page(request: Request):
    return settings.templates.TemplateResponse(request, "messenger.html")