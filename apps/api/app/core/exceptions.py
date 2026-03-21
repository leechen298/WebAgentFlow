class AppError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code or status_code


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            f"{resource} '{resource_id}' was not found.",
            status_code=404,
            code=404,
        )


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "Service is unavailable.") -> None:
        super().__init__(message, status_code=503, code=503)
