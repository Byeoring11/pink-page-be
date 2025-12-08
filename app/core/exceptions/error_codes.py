"""Error code system

Error code structure (5 digits):
- 1st digit: Category (1=General, 2=SSH, 3=WebSocket, 4=DB, 5=Business)
- 2nd-3rd digits: Sub-category
- 4th-5th digits: Specific error

Example: 20101 = SSH(2) Connection(01) Timeout(01)
"""

from enum import Enum
from typing import Dict


class ErrorCategory(str, Enum):
    """Error categories"""
    GENERAL = "1"
    SSH = "2"
    WEBSOCKET = "3"
    DATABASE = "4"
    BUSINESS = "5"


class ErrorCode(Enum):
    """Error code definitions. Each code is (code, message, http_status) tuple."""

    # 1XXX: General Errors
    INTERNAL_SERVER_ERROR = (10000, "Internal server error", 500)
    SERVICE_UNAVAILABLE = (10001, "Service temporarily unavailable", 503)
    UNKNOWN_ERROR = (10099, "Unknown error occurred", 500)

    UNAUTHORIZED = (11000, "Authentication required", 401)
    FORBIDDEN = (11001, "Access denied", 403)
    INVALID_TOKEN = (11002, "Invalid token", 401)
    TOKEN_EXPIRED = (11003, "Token expired", 401)

    VALIDATION_ERROR = (12000, "Validation failed", 422)
    INVALID_PARAMETER = (12001, "Invalid parameter", 400)
    MISSING_REQUIRED_FIELD = (12002, "Missing required field", 400)
    INVALID_FORMAT = (12003, "Invalid data format", 400)

    RESOURCE_NOT_FOUND = (13000, "Resource not found", 404)
    RESOURCE_ALREADY_EXISTS = (13001, "Resource already exists", 409)
    RESOURCE_LOCKED = (13002, "Resource is locked", 423)

    OPERATION_NOT_ALLOWED = (14000, "Operation not allowed", 403)
    QUOTA_EXCEEDED = (14001, "Quota exceeded", 429)

    # 2XXX: SSH Errors
    SSH_CONNECTION_FAILED = (20000, "SSH connection failed", 503)
    SSH_CONNECTION_TIMEOUT = (20001, "SSH connection timeout", 504)
    SSH_CONNECTION_REFUSED = (20002, "SSH connection refused", 503)
    SSH_ALREADY_CONNECTED = (20003, "Already connected to SSH", 409)
    SSH_NOT_CONNECTED = (20004, "Not connected to SSH", 400)
    SSH_CONNECTION_LOST = (20005, "SSH connection lost", 503)

    SSH_AUTH_FAILED = (21000, "SSH authentication failed", 401)
    SSH_INVALID_CREDENTIALS = (21001, "Invalid SSH credentials", 401)
    SSH_AUTH_TIMEOUT = (21002, "SSH authentication timeout", 504)
    SSH_KEY_ERROR = (21003, "SSH key error", 500)

    SSH_COMMAND_FAILED = (22000, "SSH command execution failed", 500)
    SSH_COMMAND_TIMEOUT = (22001, "SSH command timeout", 504)
    SSH_INVALID_COMMAND = (22002, "Invalid SSH command", 400)
    SSH_CHANNEL_ERROR = (22003, "SSH channel error", 500)
    SSH_SHELL_ERROR = (22004, "SSH shell error", 500)

    SSH_CONFIG_ERROR = (23000, "SSH configuration error", 500)
    SSH_INVALID_SERVER_TYPE = (23001, "Invalid server type", 400)
    SSH_SERVER_NOT_FOUND = (23002, "SSH server configuration not found", 404)

    SSH_SCP_TRANSFER_FAILED = (24000, "SCP file transfer failed", 500)
    SSH_SCP_CONFIG_NOT_FOUND = (24001, "SCP transfer configuration not found", 404)
    SSH_SCP_COMMAND_NOT_FOUND = (24002, "sshpass or scp command not found", 500)
    SSH_SCP_PERMISSION_DENIED = (24003, "SCP permission denied", 403)
    SSH_SCP_TIMEOUT = (24004, "SCP transfer timeout", 504)

    SSH_HEALTH_CHECK_FAILED = (25000, "SSH health check failed", 500)
    SSH_HEALTH_CHECK_SERVICE_START_FAILED = (25001, "Health check service start failed", 500)
    SSH_HEALTH_CHECK_SERVICE_ALREADY_RUNNING = (25002, "Health check service already running", 409)
    SSH_HEALTH_CHECK_CALLBACK_ERROR = (25003, "Health check callback execution failed", 500)

    # 3XXX: WebSocket Errors
    WS_CONNECTION_FAILED = (30000, "WebSocket connection failed", 500)
    WS_CONNECTION_CLOSED = (30001, "WebSocket connection closed", 1000)
    WS_NOT_CONNECTED = (30002, "WebSocket not connected", 400)
    WS_ALREADY_CONNECTED = (30003, "Already connected to WebSocket", 409)
    WS_CONNECTION_TIMEOUT = (30004, "WebSocket connection timeout", 504)

    WS_MESSAGE_SEND_FAILED = (31000, "WebSocket message send failed", 500)
    WS_MESSAGE_RECEIVE_FAILED = (31001, "WebSocket message receive failed", 500)
    WS_INVALID_MESSAGE_FORMAT = (31002, "Invalid message format", 400)
    WS_MESSAGE_TOO_LARGE = (31003, "Message too large", 413)
    WS_INVALID_MESSAGE_TYPE = (31004, "Invalid message type", 400)

    WS_HANDLER_NOT_FOUND = (32000, "Message handler not found", 404)
    WS_HANDLER_ERROR = (32001, "Message handler error", 500)
    WS_INVALID_ACTION = (32002, "Invalid action", 400)

    WS_BROADCAST_FAILED = (33000, "WebSocket broadcast failed", 500)
    WS_BROADCAST_PARTIAL = (33001, "WebSocket broadcast partially failed", 207)

    # 4XXX: Database Errors
    DB_CONNECTION_FAILED = (40000, "Database connection failed", 503)
    DB_CONNECTION_TIMEOUT = (40001, "Database connection timeout", 504)
    DB_CONNECTION_LOST = (40002, "Database connection lost", 503)

    DB_QUERY_FAILED = (41000, "Database query failed", 500)
    DB_INTEGRITY_ERROR = (41001, "Data integrity constraint violation", 409)
    DB_CONSTRAINT_VIOLATION = (41002, "Database constraint violation", 409)

    # 5XXX: Business Logic Errors
    # STUB Domain
    STUB_COMMAND_FAILED = (50000, "Command execution failed", 500)
    STUB_INVALID_CONNECTION_ID = (50001, "Invalid connection ID", 400)
    STUB_SESSION_EXPIRED = (50002, "Session expired", 401)
    STUB_OUTPUT_TIMEOUT = (50003, "Output wait timeout", 504)
    STUB_SESSION_ALREADY_ACTIVE = (50004, "Session already active", 409)
    STUB_SESSION_NOT_ACTIVE = (50005, "No active session", 400)
    STUB_SESSION_PERMISSION_DENIED = (50006, "Session permission denied", 403)
    STUB_SESSION_OWNER_MISMATCH = (50007, "Session owner mismatch", 403)
    STUB_RESOURCE_LOCKED = (50008, "Resource is locked", 423)
    STUB_TRANSFER_FAILED = (50009, "File transfer failed", 500)

    # Task Management Errors
    STUB_TASK_ALREADY_RUNNING = (50010, "Task already running", 409)
    STUB_TASK_NOT_FOUND = (50011, "Task not found", 404)
    STUB_TASK_CANCELLATION_TIMEOUT = (50012, "Task cancellation timeout", 504)
    STUB_TASK_CANCELLATION_FAILED = (50013, "Task cancellation failed", 500)
    STUB_TASK_CLEANUP_FAILED = (50014, "Task cleanup failed", 500)

    # Load History Errors
    STUB_LOAD_HISTORY_DB_INIT_FAILED = (50015, "Load history database initialization failed", 500)
    STUB_LOAD_HISTORY_CREATE_FAILED = (50016, "Load history creation failed", 500)
    STUB_LOAD_HISTORY_QUERY_FAILED = (50017, "Load history query failed", 500)
    STUB_LOAD_HISTORY_BATCH_NOT_FOUND = (50018, "Batch history not found", 404)
    STUB_LOAD_HISTORY_CUSTOMER_QUERY_FAILED = (50019, "Customer history query failed", 500)
    STUB_LOAD_HISTORY_DELETE_FAILED = (50020, "Load history deletion failed", 500)
    STUB_LOAD_HISTORY_INVALID_CUSTOMER_NUMBER = (50021, "Invalid customer number format", 400)
    STUB_LOAD_HISTORY_DUPLICATE_ENTRY = (50022, "Duplicate load history entry", 409)
    STUB_LOAD_HISTORY_DB_CONNECTION_FAILED = (50023, "Load history database connection failed", 503)
    STUB_LOAD_HISTORY_VALIDATION_ERROR = (50024, "Load history data validation error", 400)

    # BMX4 Domain
    BMX4_OPERATION_FAILED = (51000, "BMX4 operation failed", 500)
    BMX4_INVALID_REQUEST = (51001, "Invalid BMX4 request", 400)

    # BMX5 Domain
    BMX5_OPERATION_FAILED = (52000, "BMX5 operation failed", 500)
    BMX5_INVALID_REQUEST = (52001, "Invalid BMX5 request", 400)

    # DIFF Domain
    DIFF_COMPARISON_FAILED = (53000, "Diff comparison failed", 500)
    DIFF_INVALID_INPUT = (53001, "Invalid diff input", 400)

    @property
    def code(self) -> int:
        """Return error code"""
        return self.value[0]

    @property
    def message(self) -> str:
        """Return error message"""
        return self.value[1]

    @property
    def http_status(self) -> int:
        """Return HTTP status code"""
        return self.value[2]

    def format_message(self, **kwargs) -> str:
        """Format message with variables"""
        try:
            return self.message.format(**kwargs)
        except KeyError:
            return self.message

    def to_dict(self, detail: str = None) -> Dict:
        """Convert to dictionary for client response"""
        result = {
            "error_code": self.code,
            "message": self.message,
        }
        if detail:
            result["detail"] = detail
        return result


class WSCloseCode(Enum):
    """WebSocket close codes (RFC 6455)"""
    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    INVALID_FRAME_PAYLOAD = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013


ERROR_CATEGORY_MAP = {
    ErrorCategory.GENERAL: range(10000, 20000),
    ErrorCategory.SSH: range(20000, 30000),
    ErrorCategory.WEBSOCKET: range(30000, 40000),
    ErrorCategory.DATABASE: range(40000, 50000),
    ErrorCategory.BUSINESS: range(50000, 60000),
}


def get_error_category(error_code: int) -> ErrorCategory:
    """Get category from error code"""
    for category, code_range in ERROR_CATEGORY_MAP.items():
        if error_code in code_range:
            return category
    return ErrorCategory.GENERAL
