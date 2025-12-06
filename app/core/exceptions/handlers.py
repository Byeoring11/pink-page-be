"""Global exception handlers for FastAPI"""

import traceback
from typing import Union
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from app.core.exceptions.base import BaseAppException
from app.core.exceptions.error_codes import ErrorCode
from app.core.logger import logger


class ErrorResponse:
    """Standard error response format"""

    @staticmethod
    def create(
        error_code: int,
        message: str,
        detail: str = None,
        path: str = None,
        http_status: int = 500
    ) -> dict:
        """Create standard error response"""
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
            }
        }

        if detail:
            response["error"]["detail"] = detail

        if path:
            response["path"] = path

        return response


async def base_app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """Handle custom application exceptions"""
    log_data = exc.to_log_dict()
    log_data["path"] = request.url.path
    log_data["method"] = request.method

    if exc.http_status >= 500:
        logger.error(
            f"[{exc.code}] {exc.error_code.message}",
            extra={
                "error_code": exc.code,
                "detail": exc.detail,
                "context": log_data
            }
        )
    elif exc.http_status >= 400:
        logger.warning(
            f"[{exc.code}] {exc.error_code.message}",
            extra={
                "error_code": exc.code,
                "detail": exc.detail,
                "context": log_data
            }
        )
    else:
        logger.info(
            f"[{exc.code}] {exc.error_code.message}",
            extra={
                "error_code": exc.code,
                "detail": exc.detail,
                "context": log_data
            }
        )

    response_data = ErrorResponse.create(
        error_code=exc.code,
        message=exc.error_code.message,
        detail=exc.detail,
        path=request.url.path,
        http_status=exc.http_status
    )

    return JSONResponse(
        status_code=exc.http_status,
        content=response_data
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """Handle Pydantic validation exceptions"""
    errors = exc.errors() if hasattr(exc, 'errors') else []
    error_details = []

    for error in errors:
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "")
        error_details.append(f"{field}: {msg}")

    detail = "; ".join(error_details) if error_details else "Validation failed"

    logger.warning(
        f"[{ErrorCode.VALIDATION_ERROR.code}] Validation failed",
        extra={
            "error_code": ErrorCode.VALIDATION_ERROR.code,
            "path": request.url.path,
            "method": request.method,
            "validation_errors": errors
        }
    )

    response_data = ErrorResponse.create(
        error_code=ErrorCode.VALIDATION_ERROR.code,
        message=ErrorCode.VALIDATION_ERROR.message,
        detail=detail,
        path=request.url.path,
        http_status=422
    )

    if errors:
        response_data["error"]["validation_errors"] = errors

    return JSONResponse(status_code=422, content=response_data)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette HTTP exceptions"""
    error_code_map = {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.QUOTA_EXCEEDED,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }

    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)

    logger.warning(
        f"[{error_code.code}] HTTP {exc.status_code} - {exc.detail}",
        extra={
            "error_code": error_code.code,
            "path": request.url.path,
            "method": request.method,
            "http_status": exc.status_code
        }
    )

    response_data = ErrorResponse.create(
        error_code=error_code.code,
        message=error_code.message,
        detail=str(exc.detail) if exc.detail else None,
        path=request.url.path,
        http_status=exc.status_code
    )

    return JSONResponse(status_code=exc.status_code, content=response_data)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    tb = traceback.format_exc()
    logger.error(
        f"[{ErrorCode.INTERNAL_SERVER_ERROR.code}] Unexpected exception: {str(exc)}",
        extra={
            "error_code": ErrorCode.INTERNAL_SERVER_ERROR.code,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": tb
        }
    )

    response_data = ErrorResponse.create(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR.code,
        message=ErrorCode.INTERNAL_SERVER_ERROR.message,
        detail="Internal server error. Please contact administrator.",
        path=request.url.path,
        http_status=500
    )

    return JSONResponse(status_code=500, content=response_data)


def register_exception_handlers(app):
    """Register exception handlers to FastAPI app"""
    app.add_exception_handler(BaseAppException, base_app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Global exception handlers registered")
