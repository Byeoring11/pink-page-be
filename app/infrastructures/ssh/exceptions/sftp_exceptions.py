from typing import Optional, Any, Dict
from app.infrastructures.ssh.exceptions.ssh_exceptions import SSHBaseException, SSHConnectionError


class SFTPBaseException(SSHBaseException):
    """Base exception for all SFTP related errors."""
    pass


class SFTPConnectionError(SSHConnectionError):
    """Exception raised for SFTP connection errors."""

    def __init__(self, message: str = "Failed to establish SFTP connection",
                 host: Optional[str] = None, port: Optional[int] = None,
                 username: Optional[str] = None, cause: Optional[Exception] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, host, port, username, cause, details)


class SFTPFileError(SFTPBaseException):
    """Exception raised for file operations in SFTP."""

    def __init__(self, message: str = "SFTP file operation failed",
                 operation: Optional[str] = None, path: Optional[str] = None,
                 cause: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        file_details = {}
        if operation:
            file_details["operation"] = operation
        if path:
            file_details["path"] = path

        all_details = {**file_details, **(details or {})}

        super().__init__(message, cause, all_details)


class SFTPPermissionError(SFTPFileError):
    """Exception raised for permission errors in SFTP operations."""

    def __init__(self, message: str = "Permission denied for SFTP operation",
                 operation: Optional[str] = None, path: Optional[str] = None,
                 cause: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, operation, path, cause, details)


class SFTPNotFoundError(SFTPFileError):
    """Exception raised when a file or directory is not found."""

    def __init__(self, message: str = "File or directory not found",
                 operation: Optional[str] = None, path: Optional[str] = None,
                 cause: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, operation, path, cause, details)


class SFTPAlreadyExistsError(SFTPFileError):
    """Exception raised when a file or directory already exists."""

    def __init__(self, message: str = "File or directory already exists",
                 operation: Optional[str] = None, path: Optional[str] = None,
                 cause: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, operation, path, cause, details)
