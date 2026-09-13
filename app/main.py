from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.web.main import api_router
from app.core.configs import settings
from app.core.redis import lifespan

app = FastAPI(
    title="Room messenger",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
