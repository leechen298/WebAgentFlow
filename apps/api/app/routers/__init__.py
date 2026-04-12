"""API routers."""

from fastapi import APIRouter

from app.routers.ast import router as ast_router
from app.routers.health import router as health_router
from app.routers.recordings import router as recordings_router
from app.routers.runs import router as runs_router
from app.routers.skills import router as skills_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(recordings_router)
api_router.include_router(skills_router)
api_router.include_router(runs_router)
api_router.include_router(ast_router)

__all__ = ["api_router"]
