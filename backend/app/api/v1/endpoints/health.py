from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check():
    settings = get_settings()

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "0.1.0",
    }
