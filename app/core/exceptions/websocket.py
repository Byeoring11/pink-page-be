"""WebSocket error handlers"""

import traceback
from typing import Optional
from fastapi import WebSocket
from datetime import datetime

from app.core.exceptions.base import BaseAppException
from app.core.exceptions.error_codes import ErrorCode, WSCloseCode
from app.core.logger import logger


class WSErrorResponse:
    """WebSocket error response format"""

    @staticmethod
    def create(
        error_code: int,
        message: str,
        detail: Optional[str] = None,
        message_type: str = "error",
        **extra_data
    ) -> dict:
        """Create WebSocket error response"""
        response = {
            "type": message_type,
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
            },
            "timestamp": datetime.now().isoformat()
        }

        if detail:
            response["error"]["detail"] = detail

        if extra_data:
            response.update(extra_data)

        return response


class WebSocketErrorHandler:
    """WebSocket error handler class"""

    def __init__(self, websocket: WebSocket, connection_id: Optional[str] = None):
        self.websocket = websocket
        self.connection_id = connection_id or str(id(websocket))

    async def handle_exception(
        self,
        exc: Exception,
        send_to_client: bool = True,
        close_connection: bool = False,
        close_code: int = WSCloseCode.INTERNAL_ERROR.value
    ) -> Optional[dict]:
        """Handle exception and send error message"""
        error_response = None

        if isinstance(exc, BaseAppException):
            error_response = await self._handle_app_exception(exc, send_to_client=send_to_client)
        else:
            error_response = await self._handle_generic_exception(exc, send_to_client=send_to_client)

        if close_connection:
            await self._close_connection(close_code, exc)

        return error_response

    async def _handle_app_exception(
        self,
        exc: BaseAppException,
        send_to_client: bool = True
    ) -> Optional[dict]:
        """Handle custom application exception"""
        log_data = exc.to_log_dict()
        log_data["connection_id"] = self.connection_id

        if exc.http_status >= 500:
            logger.error(
                f"[WS:{self.connection_id}] [{exc.code}] {exc.error_code.message}",
                extra=log_data
            )
        else:
            logger.warning(
                f"[WS:{self.connection_id}] [{exc.code}] {exc.error_code.message}",
                extra=log_data
            )

        error_response = WSErrorResponse.create(
            error_code=exc.code,
            message=exc.error_code.message,
            detail=exc.detail
        )

        if send_to_client:
            await self._send_error_message(error_response)

        return error_response

    async def _handle_generic_exception(
        self,
        exc: Exception,
        send_to_client: bool = True
    ) -> Optional[dict]:
        """Handle generic exception"""
        tb = traceback.format_exc()
        logger.error(
            f"[WS:{self.connection_id}] [{ErrorCode.INTERNAL_SERVER_ERROR.code}] "
            f"Unexpected exception: {str(exc)}",
            extra={
                "connection_id": self.connection_id,
                "error_code": ErrorCode.INTERNAL_SERVER_ERROR.code,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": tb
            }
        )

        error_response = WSErrorResponse.create(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR.code,
            message="Internal server error",
            detail="Please contact administrator."
        )

        if send_to_client:
            await self._send_error_message(error_response)

        return error_response

    async def _send_error_message(self, error_response: dict) -> None:
        """Send error message to client"""
        try:
            await self.websocket.send_json(error_response)
            logger.debug(
                f"[WS:{self.connection_id}] Error message sent: {error_response['error']['code']}"
            )
        except Exception as send_error:
            logger.error(
                f"[WS:{self.connection_id}] Failed to send error message: {str(send_error)}",
                extra={
                    "connection_id": self.connection_id,
                    "original_error_code": error_response['error']['code'],
                    "send_error": str(send_error)
                }
            )

    async def _close_connection(self, close_code: int, reason: Optional[Exception] = None) -> None:
        """Close WebSocket connection"""
        try:
            reason_text = str(reason)[:100] if reason else "Connection closed"
            await self.websocket.close(code=close_code, reason=reason_text)
            logger.info(
                f"[WS:{self.connection_id}] Connection closed: code={close_code}, reason={reason_text}"
            )
        except Exception as close_error:
            logger.error(
                f"[WS:{self.connection_id}] Failed to close connection: {str(close_error)}",
                extra={
                    "connection_id": self.connection_id,
                    "close_code": close_code,
                    "close_error": str(close_error)
                }
            )


def create_error_message(error_code: ErrorCode, detail: Optional[str] = None, **extra_data) -> dict:
    """Helper function to create WebSocket error message"""
    return WSErrorResponse.create(
        error_code=error_code.code,
        message=error_code.message,
        detail=detail,
        **extra_data
    )


async def send_error_and_close(
    websocket: WebSocket,
    error_code: ErrorCode,
    detail: Optional[str] = None,
    close_code: int = WSCloseCode.INTERNAL_ERROR.value,
    connection_id: Optional[str] = None
) -> None:
    """Send error message and close connection"""
    handler = WebSocketErrorHandler(websocket, connection_id)

    error_message = create_error_message(error_code, detail)
    await handler._send_error_message(error_message)
    await handler._close_connection(close_code, None)


def handle_ws_errors(
    send_error: bool = True,
    close_on_error: bool = False,
    close_code: int = WSCloseCode.INTERNAL_ERROR.value
):
    """Decorator to add exception handling to WebSocket handler functions

    Example:
        @handle_ws_errors(send_error=True, close_on_error=False)
        async def handle_message(websocket: WebSocket, data: dict):
            # Message handling logic
            pass
    """
    def decorator(func):
        async def wrapper(websocket: WebSocket, *args, **kwargs):
            connection_id = kwargs.get('connection_id', str(id(websocket)))
            handler = WebSocketErrorHandler(websocket, connection_id)

            try:
                return await func(websocket, *args, **kwargs)
            except Exception as exc:
                await handler.handle_exception(
                    exc,
                    send_to_client=send_error,
                    close_connection=close_on_error,
                    close_code=close_code
                )

        return wrapper
    return decorator
