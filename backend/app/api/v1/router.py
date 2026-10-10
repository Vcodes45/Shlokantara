from fastapi import APIRouter

from app.api.v1.endpoints import (
    chat,
    health,
    hybrid_search,
    search,
    semantic_search,
    verses,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])

api_router.include_router(
    verses.router,
    prefix="/verses",
    tags=["verses"],
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["search"],
)

api_router.include_router(
    semantic_search.router,
    prefix="/search",
    tags=["semantic-search"],
)

api_router.include_router(
    hybrid_search.router,
    prefix="/search",
    tags=["hybrid-search"],
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"],
)
