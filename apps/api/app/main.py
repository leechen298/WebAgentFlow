from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.routers import api_router
from app.schemas.common import ApiErrorResponse

configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
def get_cors_allowed_origins() -> list[str]:
    """Parse CORS allowed origins from settings."""
    if not settings.cors_allowed_origins:
        # Default: allow localhost and common dev origins in development
        if settings.env == "development":
            return [
                "http://localhost:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
            ]
        return []
    # Parse comma-separated list
    origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",")]
    return [origin for origin in origins if origin]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiErrorResponse(code=exc.code, msg=exc.message).model_dump(),
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    data = exc.detail if isinstance(exc.detail, dict | list) else None
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiErrorResponse(code=exc.status_code, msg=message, data=data).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ApiErrorResponse(code=422, msg="Validation error.", data=exc.errors()).model_dump(),
    )


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.env == "development",
    )


if __name__ == "__main__":
    run()
