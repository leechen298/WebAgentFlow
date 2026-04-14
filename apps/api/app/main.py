from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.locale import normalize_locale, set_locale
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

@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    """Extract locale from request headers and set it for the request context."""
    raw = request.headers.get("x-locale") or request.headers.get("accept-language", "")
    # Accept-Language can be complex ("en-US,en;q=0.9,zh;q=0.8"), take the first tag
    first_tag = raw.split(",")[0].split(";")[0] if raw else ""
    set_locale(normalize_locale(first_tag))
    return await call_next(request)


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


def format_validation_error_message(errors: list[dict]) -> str:
    """
    Format validation errors into a human-readable message.
    Takes the first error or combines multiple errors for clarity.
    """
    if not errors:
        return "Validation error."

    # Use the first error for the main message
    first_error = errors[0]
    loc = first_error.get("loc", [])
    msg = first_error.get("msg", "Invalid value")

    # Format location: ["body", "skill_id"] -> "body.skill_id"
    loc_str = ".".join(str(x) for x in loc if x != "body") if loc else "field"

    # Build user-friendly message
    if len(errors) == 1:
        return f"{loc_str}: {msg}"
    else:
        return f"{loc_str}: {msg} (and {len(errors) - 1} more errors)"


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = format_validation_error_message(errors)
    return JSONResponse(
        status_code=422,
        content=ApiErrorResponse(code=422, msg=message, data=errors).model_dump(),
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
