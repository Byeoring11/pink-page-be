from typing import Optional, Any, Dict


class SSHBaseException(Exception):
    """Base exception for all SSH related errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.cause = cause
        self.details = details or {}

        # Create a detailed message including the cause if available
        detailed_message = message
        if cause:
            detailed_message += f" - Caused by: {str(cause)}"

        super().__init__(detailed_message)


class SSHConnectionError(SSHBaseException):
    """Exception raised for SSH connection errors."""

    def __init__(self,
                 message: str = "Failed to establish SSH connection",
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 username: Optional[str] = None,
                 cause: Optional[Exception] = None,
                 details: Optional[Dict[str, Any]] = None):
        connection_details = {}
        if host:
            connection_details["host"] = host
        if port:
            connection_details["port"] = port
        if username:
            connection_details["username"] = username

        all_details = {**connection_details, **(details or {})}

        super().__init__(message, cause, all_details)


class SSHCommandError(SSHBaseException):
    """Exception raised when a command execution fails."""

    def __init__(
        self,
        message: str = "Command execution failed",
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        command_details = {}
        if command:
            command_details["command"] = command
        if exit_code is not None:
            command_details["exit_code"] = exit_code
        if stdout:
            command_details["stdout"] = stdout
        if stderr:
            command_details["stderr"] = stderr

        all_details = {**command_details, **(details or {})}

        super().__init__(message, cause, all_details)


class SSHTimeoutError(SSHBaseException):
    """Exception raised when an SSH operation times out."""

    def __init__(
        self,
        message: str = "SSH operation timed out",
        operation: Optional[str] = None,
        timeout: Optional[int] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        timeout_details = {}
        if operation:
            timeout_details["operation"] = operation
        if timeout:
            timeout_details["timeout_seconds"] = timeout

        all_details = {**timeout_details, **(details or {})}

        super().__init__(message, cause, all_details)
