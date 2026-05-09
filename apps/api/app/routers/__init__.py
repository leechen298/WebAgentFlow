"""API routers."""

from fastapi import APIRouter

from app.routers.ast import router as ast_router
from app.routers.conversation import router as conversation_router
from app.routers.exploration import router as exploration_router
from app.routers.health import router as health_router
from app.routers.validation_api import router as validation_api_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(ast_router)
api_router.include_router(exploration_router)
api_router.include_router(validation_api_router)
api_router.include_router(conversation_router)

__all__ = ["api_router"]
