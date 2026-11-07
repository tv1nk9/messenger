import os
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

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
    GZipMiddleware,
    minimum_size=settings.GZIP_SIZE,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


REACT_BUILD_DIR = os.path.join("static", "react")


def _render_react_page(request: Request, page_title: str) -> HTMLResponse:
    """Отдаёт собранный React SPA (frontend/ -> static/react), подставляя хэшированные ассеты."""
    index_path = os.path.join(REACT_BUILD_DIR, "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse(
            "<h1>React-сборка не найдена</h1>"
            "<p>Выполните <code>cd frontend && npm install && npm run build</code>.</p>",
            status_code=503,
        )
    with open(index_path, encoding="utf-8") as f:
        html = f.read()
    html = re.sub(r"<title>[^<]*</title>", f"<title>{page_title}</title>", html, count=1)
    return HTMLResponse(html)


@app.get("/login_page", response_class=HTMLResponse, summary="Auth page")
async def get_auth_page(request: Request):
    return _render_react_page(request, "Вход — Мессенджер")


@app.get("/", response_class=HTMLResponse, summary="Chats page")
async def main_page(request: Request):
    return _render_react_page(request, "Мессенджер")