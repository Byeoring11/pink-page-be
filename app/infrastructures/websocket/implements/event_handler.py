from typing import Dict, Any, Callable, Awaitable, List

from app.core.logger import logger
from app.infrastructures.websocket.interfaces import WebSocketEventHandlerInterface


class WebSocketEventHandler(WebSocketEventHandlerInterface):
    """WebSocket 이벤트 핸들러 구현"""

    def __init__(self):
        self.event_handlers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}

    def register_event_handler(self, event_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """특정 이벤트에 대한 핸들러 등록"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
        logger.debug(f"'{event_name}' 이벤트가 핸들러에 등록됐습니다.")

    async def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """특정 이벤트 처리"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"이벤트 '{event_name}' 처리 중 오류 발생: {str(e)}")
        else:
            logger.warning(f"'{event_name}'이벤트가 핸들러에 등록되어있지 않습니다.")
