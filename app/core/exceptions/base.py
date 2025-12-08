"""커스텀 예외 클래스 정의

예외 계층도:
    BaseAppException
    |-- GeneralException (일반 예외)
    |   |-- ValidationException
    |   |-- ResourceNotFoundException
    |   +-- UnauthorizedException
    |-- SSHException (SSH 예외)
    |   |-- SSHConnectionException
    |   |-- SSHAuthException
    |   |-- SSHCommandException
    |   |-- SSHTimeoutException
    |   |-- SSHSCPException
    |   |-- SSHHealthCheckException
    |   +-- SSHHealthCheckServiceException
    |-- WebSocketException (웹소켓 예외)
    |   |-- WSConnectionException
    |   |-- WSMessageException
    |   |-- WSInvalidMessageException
    |   |-- WSHandlerNotFoundException
    |   +-- WSBroadcastException
    |-- DatabaseException (DB 예외)
    |   |-- DBConnectionException
    |   +-- DBQueryException
    +-- BusinessException (비즈니스 로직 예외)
        |-- StubException (대응답 로직)
        |   |-- StubCommandFailedException
        |   |-- StubInvalidConnectionException
        |   |-- StubSessionExpiredException
        |   |-- StubSessionAlreadyActiveException
        |   |-- StubSessionNotActiveException
        |   |-- StubSessionPermissionDeniedException
        |   |-- StubTransferFailedException
        |   |-- StubTaskAlreadyRunningException (Task 관리)
        |   |-- StubTaskNotFoundException
        |   |-- StubTaskCancellationTimeoutException
        |   |-- StubTaskCancellationFailedException
        |   |-- StubTaskCleanupFailedException
        |   |-- StubLoadHistoryException (작업 이력 관리)
        |   |   |-- StubLoadHistoryDBInitException
        |   |   |-- StubLoadHistoryCreateException
        |   |   |-- StubLoadHistoryQueryException
        |   |   |-- StubLoadHistoryBatchNotFoundException
        |   |   |-- StubLoadHistoryDeleteException
        |   |   |-- StubLoadHistoryValidationException
        |   |   |-- StubLoadHistoryDuplicateException
        |   |   +-- StubLoadHistoryDBConnectionException
        |-- Bmx4Exception
        |-- Bmx5Exception
        +-- DiffException
"""

from typing import Optional, Dict, Any
from app.core.exceptions.error_codes import ErrorCode, get_error_category, ErrorCategory


class BaseAppException(Exception):
    """Base application exception. All custom exceptions inherit from this."""

    def __init__(
        self,
        error_code: ErrorCode,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.error_code = error_code
        self.detail = detail
        self.context = context or {}
        self.original_exception = original_exception

        message = error_code.message
        if detail:
            message = f"{message}: {detail}"

        super().__init__(message)

    @property
    def code(self) -> int:
        return self.error_code.code

    @property
    def http_status(self) -> int:
        return self.error_code.http_status

    @property
    def category(self) -> ErrorCategory:
        return get_error_category(self.code)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for client response"""
        result = {
            "error_code": self.code,
            "message": self.error_code.message,
            "category": self.category.value,
        }
        if self.detail:
            result["detail"] = self.detail
        return result

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to logging dictionary with more information"""
        log_data = self.to_dict()
        if self.context:
            log_data["context"] = self.context
        if self.original_exception:
            log_data["original_error"] = {
                "type": type(self.original_exception).__name__,
                "message": str(self.original_exception),
            }
        return log_data

    def __str__(self) -> str:
        return f"[{self.code}] {self.error_code.message}" + (
            f": {self.detail}" if self.detail else ""
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"code={self.code}, "
            f"message='{self.error_code.message}', "
            f"detail='{self.detail}'"
            f")"
        )


# General Exceptions (1XXX)
class GeneralException(BaseAppException):
    """General exception"""
    pass


class ValidationException(GeneralException):
    """Validation exception"""
    def __init__(self, detail: Optional[str] = None, field: Optional[str] = None, **kwargs):
        if field and not detail:
            detail = f"'{field}' field validation failed"
        super().__init__(ErrorCode.VALIDATION_ERROR, detail=detail, **kwargs)


class ResourceNotFoundException(GeneralException):
    """Resource not found"""
    def __init__(self, resource_type: str, resource_id: Any, **kwargs):
        detail = f"{resource_type} '{resource_id}' not found"
        super().__init__(
            ErrorCode.RESOURCE_NOT_FOUND,
            detail=detail,
            context={"resource_type": resource_type, "resource_id": resource_id},
            **kwargs
        )


class UnauthorizedException(GeneralException):
    """Unauthorized"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.UNAUTHORIZED, detail=detail, **kwargs)


# SSH Exceptions (2XXX)
class SSHException(BaseAppException):
    """SSH related base exception"""
    pass


class SSHConnectionException(SSHException):
    """SSH connection exception"""
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.SSH_CONNECTION_FAILED,
        **kwargs
    ):
        context = {}
        if host:
            context["host"] = host
        if port:
            context["port"] = port
        super().__init__(error_code, detail=detail, context=context, **kwargs)


class SSHAuthException(SSHException):
    """SSH authentication exception"""
    def __init__(
        self,
        username: Optional[str] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.SSH_AUTH_FAILED,
        **kwargs
    ):
        context = {}
        if username:
            context["username"] = username
        super().__init__(error_code, detail=detail, context=context, **kwargs)


class SSHCommandException(SSHException):
    """SSH command execution exception"""
    def __init__(
        self,
        command: Optional[str] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.SSH_COMMAND_FAILED,
        **kwargs
    ):
        context = {}
        if command:
            context["command"] = command
        super().__init__(error_code, detail=detail, context=context, **kwargs)


class SSHTimeoutException(SSHException):
    """SSH timeout exception"""
    def __init__(
        self,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        detail = f"Operation '{operation}' timed out ({timeout_seconds}s)" if operation else None
        context = {}
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        if operation:
            context["operation"] = operation
        super().__init__(ErrorCode.SSH_CONNECTION_TIMEOUT, detail=detail, context=context, **kwargs)


class SSHSCPException(SSHException):
    """SSH SCP transfer exception"""
    def __init__(
        self,
        transfer_name: Optional[str] = None,
        src: Optional[str] = None,
        dst: Optional[str] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.SSH_SCP_TRANSFER_FAILED,
        **kwargs
    ):
        context = {}
        if transfer_name:
            context["transfer_name"] = transfer_name
        if src:
            context["src"] = src
        if dst:
            context["dst"] = dst
        super().__init__(error_code, detail=detail, context=context, **kwargs)


class SSHHealthCheckException(SSHException):
    """SSH health check exception"""
    def __init__(
        self,
        server_name: Optional[str] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.SSH_HEALTH_CHECK_FAILED,
        **kwargs
    ):
        context = {}
        if server_name:
            context["server_name"] = server_name
        super().__init__(error_code, detail=detail, context=context, **kwargs)


class SSHHealthCheckServiceException(SSHException):
    """SSH health check service lifecycle exception"""
    def __init__(
        self,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.SSH_HEALTH_CHECK_SERVICE_START_FAILED,
        **kwargs
    ):
        super().__init__(error_code, detail=detail, **kwargs)


# WebSocket Exceptions (3XXX)
class WebSocketException(BaseAppException):
    """WebSocket related base exception"""
    pass


class WSConnectionException(WebSocketException):
    """WebSocket connection exception"""
    def __init__(
        self,
        connection_id: Optional[str] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.WS_CONNECTION_FAILED,
        **kwargs
    ):
        context = {}
        if connection_id:
            context["connection_id"] = connection_id
        super().__init__(error_code, detail=detail, context=context, **kwargs)


class WSMessageException(WebSocketException):
    """WebSocket message exception"""
    def __init__(
        self,
        message_type: Optional[str] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.WS_MESSAGE_SEND_FAILED,
        **kwargs
    ):
        context = {}
        if message_type:
            context["message_type"] = message_type
        super().__init__(error_code, detail=detail, context=context, **kwargs)


class WSInvalidMessageException(WebSocketException):
    """Invalid WebSocket message"""
    def __init__(self, message_data: Optional[Any] = None, reason: Optional[str] = None, **kwargs):
        detail = f"Message format error: {reason}" if reason else None
        context = {}
        if message_data:
            context["message_data"] = str(message_data)[:200]
        super().__init__(ErrorCode.WS_INVALID_MESSAGE_FORMAT, detail=detail, context=context, **kwargs)


class WSHandlerNotFoundException(WebSocketException):
    """WebSocket handler not found"""
    def __init__(self, message_type: str, **kwargs):
        detail = f"Handler not found for message type '{message_type}'"
        super().__init__(
            ErrorCode.WS_HANDLER_NOT_FOUND,
            detail=detail,
            context={"message_type": message_type},
            **kwargs
        )


class WSBroadcastException(WebSocketException):
    """WebSocket broadcast exception"""
    def __init__(
        self,
        total_connections: Optional[int] = None,
        failed_connections: Optional[int] = None,
        detail: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.WS_BROADCAST_FAILED,
        **kwargs
    ):
        context = {}
        if total_connections is not None:
            context["total_connections"] = total_connections
        if failed_connections is not None:
            context["failed_connections"] = failed_connections
        super().__init__(error_code, detail=detail, context=context, **kwargs)


# Database Exceptions (4XXX)
class DatabaseException(BaseAppException):
    """Database related base exception"""
    pass


class DBConnectionException(DatabaseException):
    """Database connection exception"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.DB_CONNECTION_FAILED, detail=detail, **kwargs)


class DBQueryException(DatabaseException):
    """Database query exception"""
    def __init__(self, query: Optional[str] = None, detail: Optional[str] = None, **kwargs):
        context = {}
        if query:
            context["query"] = query[:500]
        super().__init__(ErrorCode.DB_QUERY_FAILED, detail=detail, context=context, **kwargs)


# Business Logic Exceptions (5XXX)
class BusinessException(BaseAppException):
    """Business logic related base exception"""
    pass


# STUB Domain Exceptions
class StubException(BusinessException):
    """STUB domain exception"""
    pass


class StubCommandFailedException(StubException):
    """Command execution failed"""
    def __init__(self, command: Optional[str] = None, detail: Optional[str] = None, **kwargs):
        context = {}
        if command:
            context["command"] = command
        super().__init__(ErrorCode.STUB_COMMAND_FAILED, detail=detail, context=context, **kwargs)


class StubInvalidConnectionException(StubException):
    """Invalid connection ID"""
    def __init__(self, connection_id: str, **kwargs):
        detail = f"Invalid connection ID: {connection_id}"
        super().__init__(
            ErrorCode.STUB_INVALID_CONNECTION_ID,
            detail=detail,
            context={"connection_id": connection_id},
            **kwargs
        )


class StubSessionExpiredException(StubException):
    """Session expired"""
    def __init__(self, session_id: Optional[str] = None, **kwargs):
        detail = f"Session '{session_id}' has expired" if session_id else None
        context = {}
        if session_id:
            context["session_id"] = session_id
        super().__init__(ErrorCode.STUB_SESSION_EXPIRED, detail=detail, context=context, **kwargs)


class StubSessionAlreadyActiveException(StubException):
    """Session already active"""
    def __init__(self, session_owner: Optional[str] = None, **kwargs):
        detail = f"Session is already active (owner: {session_owner})" if session_owner else None
        context = {}
        if session_owner:
            context["session_owner"] = session_owner
        super().__init__(ErrorCode.STUB_SESSION_ALREADY_ACTIVE, detail=detail, context=context, **kwargs)


class StubSessionNotActiveException(StubException):
    """No active session"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.STUB_SESSION_NOT_ACTIVE, detail=detail, **kwargs)


class StubSessionPermissionDeniedException(StubException):
    """Session permission denied"""
    def __init__(
        self,
        session_owner: Optional[str] = None,
        requester: Optional[str] = None,
        **kwargs
    ):
        detail = f"Only session owner ({session_owner}) can perform this action" if session_owner else None
        context = {}
        if session_owner:
            context["session_owner"] = session_owner
        if requester:
            context["requester"] = requester
        super().__init__(ErrorCode.STUB_SESSION_PERMISSION_DENIED, detail=detail, context=context, **kwargs)


class StubTransferFailedException(StubException):
    """File transfer failed"""
    def __init__(
        self,
        transfer_name: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        context = {}
        if transfer_name:
            context["transfer_name"] = transfer_name
        super().__init__(ErrorCode.STUB_TRANSFER_FAILED, detail=detail, context=context, **kwargs)


# Task Management Exceptions
class StubTaskAlreadyRunningException(StubException):
    """Task already running for this connection"""
    def __init__(
        self,
        connection_id: Optional[str] = None,
        task_id: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        if not detail and connection_id:
            detail = f"A task is already running for connection: {connection_id}"
        context = {}
        if connection_id:
            context["connection_id"] = connection_id
        if task_id:
            context["task_id"] = task_id
        super().__init__(ErrorCode.STUB_TASK_ALREADY_RUNNING, detail=detail, context=context, **kwargs)


class StubTaskNotFoundException(StubException):
    """Task not found for cancellation or query"""
    def __init__(
        self,
        connection_id: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        if not detail and connection_id:
            detail = f"No task found for connection: {connection_id}"
        context = {}
        if connection_id:
            context["connection_id"] = connection_id
        super().__init__(ErrorCode.STUB_TASK_NOT_FOUND, detail=detail, context=context, **kwargs)


class StubTaskCancellationTimeoutException(StubException):
    """Task cancellation timed out"""
    def __init__(
        self,
        connection_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        if not detail and timeout_seconds:
            detail = f"Task cancellation timed out after {timeout_seconds} seconds"
        context = {}
        if connection_id:
            context["connection_id"] = connection_id
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        super().__init__(ErrorCode.STUB_TASK_CANCELLATION_TIMEOUT, detail=detail, context=context, **kwargs)


class StubTaskCancellationFailedException(StubException):
    """Task cancellation failed unexpectedly"""
    def __init__(
        self,
        connection_id: Optional[str] = None,
        reason: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        if not detail and reason:
            detail = f"Task cancellation failed: {reason}"
        context = {}
        if connection_id:
            context["connection_id"] = connection_id
        if reason:
            context["reason"] = reason
        super().__init__(ErrorCode.STUB_TASK_CANCELLATION_FAILED, detail=detail, context=context, **kwargs)


class StubTaskCleanupFailedException(StubException):
    """Task cleanup after completion or cancellation failed"""
    def __init__(
        self,
        connection_id: Optional[str] = None,
        cleanup_operation: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        if not detail and cleanup_operation:
            detail = f"Task cleanup failed during: {cleanup_operation}"
        context = {}
        if connection_id:
            context["connection_id"] = connection_id
        if cleanup_operation:
            context["cleanup_operation"] = cleanup_operation
        super().__init__(ErrorCode.STUB_TASK_CLEANUP_FAILED, detail=detail, context=context, **kwargs)


# Load History Exceptions
class StubLoadHistoryException(StubException):
    """Base exception for load history operations"""
    pass


class StubLoadHistoryDBInitException(StubLoadHistoryException):
    """Database initialization failed"""
    def __init__(
        self,
        db_path: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        context = {}
        if db_path:
            context["db_path"] = db_path
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_DB_INIT_FAILED,
            detail=detail,
            context=context,
            **kwargs
        )


class StubLoadHistoryCreateException(StubLoadHistoryException):
    """Load history creation failed"""
    def __init__(
        self,
        batch_id: Optional[str] = None,
        customer_count: Optional[int] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        context = {}
        if batch_id:
            context["batch_id"] = batch_id
        if customer_count is not None:
            context["customer_count"] = customer_count
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_CREATE_FAILED,
            detail=detail,
            context=context,
            **kwargs
        )


class StubLoadHistoryQueryException(StubLoadHistoryException):
    """Load history query failed"""
    def __init__(
        self,
        query_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        context = {}
        if query_type:
            context["query_type"] = query_type
        if filters:
            context["filters"] = filters
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_QUERY_FAILED,
            detail=detail,
            context=context,
            **kwargs
        )


class StubLoadHistoryBatchNotFoundException(StubLoadHistoryException):
    """Batch history not found"""
    def __init__(
        self,
        batch_id: str,
        **kwargs
    ):
        detail = f"No history found for batch ID: {batch_id}"
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_BATCH_NOT_FOUND,
            detail=detail,
            context={"batch_id": batch_id},
            **kwargs
        )


class StubLoadHistoryDeleteException(StubLoadHistoryException):
    """Load history deletion failed"""
    def __init__(
        self,
        retention_days: Optional[int] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        context = {}
        if retention_days is not None:
            context["retention_days"] = retention_days
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_DELETE_FAILED,
            detail=detail,
            context=context,
            **kwargs
        )


class StubLoadHistoryValidationException(StubLoadHistoryException):
    """Load history data validation error"""
    def __init__(
        self,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        if not detail and field:
            detail = f"Validation failed for field '{field}'"
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)[:100]  # Limit length
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_VALIDATION_ERROR,
            detail=detail,
            context=context,
            **kwargs
        )


class StubLoadHistoryDuplicateException(StubLoadHistoryException):
    """Duplicate load history entry"""
    def __init__(
        self,
        batch_id: Optional[str] = None,
        customer_number: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        if not detail and batch_id and customer_number:
            detail = f"Duplicate entry for batch '{batch_id}' and customer '{customer_number}'"
        context = {}
        if batch_id:
            context["batch_id"] = batch_id
        if customer_number:
            context["customer_number"] = customer_number
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_DUPLICATE_ENTRY,
            detail=detail,
            context=context,
            **kwargs
        )


class StubLoadHistoryDBConnectionException(StubLoadHistoryException):
    """Load history database connection failed"""
    def __init__(
        self,
        db_path: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        context = {}
        if db_path:
            context["db_path"] = db_path
        super().__init__(
            ErrorCode.STUB_LOAD_HISTORY_DB_CONNECTION_FAILED,
            detail=detail,
            context=context,
            **kwargs
        )


# BMX4 Domain Exceptions
class Bmx4Exception(BusinessException):
    """BMX4 domain exception"""
    pass


class Bmx4OperationFailedException(Bmx4Exception):
    """BMX4 operation failed"""
    def __init__(self, operation: Optional[str] = None, detail: Optional[str] = None, **kwargs):
        context = {}
        if operation:
            context["operation"] = operation
        super().__init__(ErrorCode.BMX4_OPERATION_FAILED, detail=detail, context=context, **kwargs)


class Bmx4InvalidRequestException(Bmx4Exception):
    """Invalid BMX4 request"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.BMX4_INVALID_REQUEST, detail=detail, **kwargs)


# BMX5 Domain Exceptions
class Bmx5Exception(BusinessException):
    """BMX5 domain exception"""
    pass


class Bmx5OperationFailedException(Bmx5Exception):
    """BMX5 operation failed"""
    def __init__(self, operation: Optional[str] = None, detail: Optional[str] = None, **kwargs):
        context = {}
        if operation:
            context["operation"] = operation
        super().__init__(ErrorCode.BMX5_OPERATION_FAILED, detail=detail, context=context, **kwargs)


class Bmx5InvalidRequestException(Bmx5Exception):
    """Invalid BMX5 request"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.BMX5_INVALID_REQUEST, detail=detail, **kwargs)


# DIFF Domain Exceptions
class DiffException(BusinessException):
    """DIFF domain exception"""
    pass


class DiffComparisonFailedException(DiffException):
    """Diff comparison failed"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.DIFF_COMPARISON_FAILED, detail=detail, **kwargs)


class DiffInvalidInputException(DiffException):
    """Invalid diff input"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.DIFF_INVALID_INPUT, detail=detail, **kwargs)


# Helper Functions
def create_exception_from_error_code(
    error_code: ErrorCode,
    detail: Optional[str] = None,
    **kwargs
) -> BaseAppException:
    """Create appropriate exception from error code"""
    category = get_error_category(error_code.code)

    if category == ErrorCategory.SSH:
        return SSHException(error_code, detail=detail, **kwargs)
    elif category == ErrorCategory.WEBSOCKET:
        return WebSocketException(error_code, detail=detail, **kwargs)
    elif category == ErrorCategory.DATABASE:
        return DatabaseException(error_code, detail=detail, **kwargs)
    elif category == ErrorCategory.BUSINESS:
        return BusinessException(error_code, detail=detail, **kwargs)
    else:
        return GeneralException(error_code, detail=detail, **kwargs)
