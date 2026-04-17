"""API routers."""

from fastapi import APIRouter

from app.routers.ast import router as ast_router
from app.routers.exploration import router as exploration_router
from app.routers.health import router as health_router
from app.routers.learning_feedback import router as learning_feedback_router
from app.routers.learning_paths import router as learning_paths_router
from app.routers.learning_runs import router as learning_runs_router
from app.routers.learning_success_criteria import router as learning_success_criteria_router
from app.routers.recordings import router as recordings_router
from app.routers.runs import router as runs_router
from app.routers.skills import router as skills_router
from app.routers.validation_api import router as validation_api_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(recordings_router)
api_router.include_router(skills_router)
api_router.include_router(runs_router)
api_router.include_router(ast_router)
api_router.include_router(learning_success_criteria_router)
api_router.include_router(learning_feedback_router)
api_router.include_router(learning_paths_router)
api_router.include_router(learning_runs_router)
api_router.include_router(exploration_router)
api_router.include_router(validation_api_router)

__all__ = ["api_router"]
