"""One consistent error format for the whole API.

Every error response looks like:
    {"detail": "Human-readable message", "code": "MACHINE_READABLE_CODE"}

Validation errors also include which fields were wrong:
    {"detail": "...", "code": "VALIDATION_ERROR", "fields": {"email": "Invalid email"}}
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

VALIDATION_ERROR_CODE = "VALIDATION_ERROR"
PYDANTIC_VALUE_ERROR_PREFIX = "Value error, "

# Default codes for plain HTTP errors raised by the framework itself (e.g. unknown URL).
DEFAULT_CODES_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
}


class AppError(Exception):
    """Raise this anywhere in the app to return a clean, predictable error response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers
        self.fields = fields


def field_validation_error(fields: dict[str, str]) -> AppError:
    """A 422 for rules Pydantic cannot check alone (e.g. comparing a new value with a saved one)."""
    return AppError(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        VALIDATION_ERROR_CODE,
        "Some fields are invalid. Please check and try again.",
        fields=fields,
    )


def _error_body(message: str, code: str) -> dict[str, object]:
    return {"detail": message, "code": code}


async def handle_app_error(_request: Request, error: AppError) -> JSONResponse:
    body = _error_body(error.message, error.code)
    if error.fields:
        body["fields"] = error.fields
    return JSONResponse(status_code=error.status_code, content=body, headers=error.headers)


async def handle_http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    code = DEFAULT_CODES_BY_STATUS.get(error.status_code, "HTTP_ERROR")
    return JSONResponse(status_code=error.status_code, content=_error_body(str(error.detail), code))


async def handle_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    """Reshape FastAPI's detailed validation list into a simple {field: message} map for forms."""
    fields: dict[str, str] = {}
    for issue in error.errors():
        # "loc" looks like ("body", "email"); drop the "body"/"query" prefix to get the field name.
        field_path = [str(part) for part in issue["loc"] if part not in ("body", "query", "path")]
        field_name = ".".join(field_path) or "request"
        # Our own validators raise ValueError, which Pydantic prefixes with "Value error, ".
        message = issue["msg"].removeprefix(PYDANTIC_VALUE_ERROR_PREFIX)
        fields.setdefault(field_name, message)

    body = _error_body("Some fields are invalid. Please check and try again.", VALIDATION_ERROR_CODE)
    body["fields"] = fields
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Attach all error handlers to the app in one call."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
