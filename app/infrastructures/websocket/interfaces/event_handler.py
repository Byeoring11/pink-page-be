from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Awaitable


class WebSocketEventHandlerInterface(ABC):
    """WebSocket 이벤트 처리를 위한 인터페이스"""

    @abstractmethod
    def register_event_handler(self, event_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """특정 이벤트에 대한 핸들러 등록"""
        pass

    @abstractmethod
    async def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """특정 이벤트 처리"""
        pass
