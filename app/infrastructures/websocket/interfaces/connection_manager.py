from abc import ABC, abstractmethod
from typing import List, Any, Optional
from fastapi import WebSocket


class WebSocketConnectionManagerInterface(ABC):
    """WebSocket 연결 관리를 위한 인터페이스"""

    @abstractmethod
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """클라이언트 연결을 수락하고 저장"""
        pass

    @abstractmethod
    async def disconnect(self, client_id: str) -> None:
        """클라이언트 연결 해제"""
        pass

    @abstractmethod
    async def send_message(self, client_id: str, message: Any) -> None:
        """특정 클라이언트에게 메시지 전송"""
        pass

    @abstractmethod
    async def broadcast(self, message: Any, exclude: Optional[List[str]] = None) -> None:
        """모든 클라이언트에게 메시지 브로드캐스트"""
        pass

    @abstractmethod
    def get_client_count(self) -> int:
        """연결된 클라이언트 수 반환"""
        pass
