"""Exception handling package for the application

This package provides:
- Error codes (error_codes.py)
- Custom exception classes (base.py)
- FastAPI exception handlers (handlers.py)
- WebSocket exception handlers (websocket.py)
"""

# Error codes
from app.core.exceptions.error_codes import (
    ErrorCode,
    ErrorCategory,
    WSCloseCode,
    get_error_category,
)

# Base exceptions
from app.core.exceptions.base import (
    BaseAppException,
    GeneralException,
    ValidationException,
    ResourceNotFoundException,
    UnauthorizedException,
    SSHException,
    SSHConnectionException,
    SSHAuthException,
    SSHCommandException,
    SSHTimeoutException,
    SSHSCPException,
    SSHHealthCheckException,
    SSHHealthCheckServiceException,
    WebSocketException,
    WSConnectionException,
    WSMessageException,
    WSInvalidMessageException,
    WSHandlerNotFoundException,
    WSBroadcastException,
    DatabaseException,
    DBConnectionException,
    DBQueryException,
    BusinessException,
    StubException,
    StubCommandFailedException,
    StubInvalidConnectionException,
    StubSessionExpiredException,
    StubSessionAlreadyActiveException,
    StubSessionNotActiveException,
    StubSessionPermissionDeniedException,
    StubTransferFailedException,
    Bmx4Exception,
    Bmx4OperationFailedException,
    Bmx4InvalidRequestException,
    Bmx5Exception,
    Bmx5OperationFailedException,
    Bmx5InvalidRequestException,
    DiffException,
    DiffComparisonFailedException,
    DiffInvalidInputException,
    create_exception_from_error_code,
)

# FastAPI handlers
from app.core.exceptions.handlers import (
    register_exception_handlers,
    ErrorResponse,
)

# WebSocket handlers
from app.core.exceptions.websocket import (
    WebSocketErrorHandler,
    WSErrorResponse,
    create_error_message,
    send_error_and_close,
    handle_ws_errors,
)

__all__ = [
    # Error codes
    "ErrorCode",
    "ErrorCategory",
    "WSCloseCode",
    "get_error_category",
    # Base exceptions
    "BaseAppException",
    "GeneralException",
    "ValidationException",
    "ResourceNotFoundException",
    "UnauthorizedException",
    "SSHException",
    "SSHConnectionException",
    "SSHAuthException",
    "SSHCommandException",
    "SSHTimeoutException",
    "SSHSCPException",
    "SSHHealthCheckException",
    "SSHHealthCheckServiceException",
    "WebSocketException",
    "WSConnectionException",
    "WSMessageException",
    "WSInvalidMessageException",
    "WSHandlerNotFoundException",
    "WSBroadcastException",
    "DatabaseException",
    "DBConnectionException",
    "DBQueryException",
    "BusinessException",
    "StubException",
    "StubCommandFailedException",
    "StubInvalidConnectionException",
    "StubSessionExpiredException",
    "StubSessionAlreadyActiveException",
    "StubSessionNotActiveException",
    "StubSessionPermissionDeniedException",
    "StubTransferFailedException",
    "Bmx4Exception",
    "Bmx4OperationFailedException",
    "Bmx4InvalidRequestException",
    "Bmx5Exception",
    "Bmx5OperationFailedException",
    "Bmx5InvalidRequestException",
    "DiffException",
    "DiffComparisonFailedException",
    "DiffInvalidInputException",
    "create_exception_from_error_code",
    # FastAPI handlers
    "register_exception_handlers",
    "ErrorResponse",
    # WebSocket handlers
    "WebSocketErrorHandler",
    "WSErrorResponse",
    "create_error_message",
    "send_error_and_close",
    "handle_ws_errors",
]
