from typing import Optional, Dict, Any


class WebSocketException(Exception):
    """WebSocket 관련 기본 예외 클래스"""
    def __init__(self, message: str, code: int = 1000, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ConnectionClosedException(WebSocketException):
    """연결이 닫힌 경우의 예외"""
    def __init__(
        self,
        message: str = "WebSocket connection is closed",
        code: int = 1000,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details)


class RateLimitException(WebSocketException):
    """요청 제한 초과 예외"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: int = 4029,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details)
