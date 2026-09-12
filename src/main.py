from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from starlette.middleware.sessions import SessionMiddleware

from src.admin import setup_admin
from src.auth.routers import auth_router
from src.config import get_settings
from src.matches import matches_router
from src.messages import messages_router
from src.requests import requests_router
from src.search import search_router

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().SECRET_KEY,
    https_only=get_settings().MODE == "PROD",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(requests_router)
app.include_router(matches_router)
app.include_router(messages_router)
app.include_router(search_router)
setup_admin(app)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


add_pagination(app)
