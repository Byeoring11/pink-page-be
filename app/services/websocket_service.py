import asyncio
from typing import Set
from fastapi import WebSocket
from app.schemas.websocket import WebSocketMessage, ClientMessage


class WebsocketService:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.lock = asyncio.Lock()

    # 외부 구현 (public)
    async def connect(self, websocket: WebSocket) -> None:
        """파사드: 연결 프로세스 전체 처리"""
        await self._accept_connection(websocket)
        await self._add_connection(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """파사드: 연결 해제 프로세스 전체 처리"""
        await self._remove_connection(websocket)

    async def broadcast(self, message: WebSocketMessage, exclude: WebSocket = None) -> None:
        """모든 활성 연결에 메시지 브로드캐스트"""
        connections = await self._get_active_connections()

        for connection in connections:
            if connection != exclude:
                try:
                    await self.send_message(connection, message)
                except Exception:
                    pass

    async def send_message(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        """단일 클라이언트에게 메시지 전송"""
        await websocket.send_json(message)

    @staticmethod
    async def receive_message(websocket: WebSocket) -> ClientMessage:
        """클라이언트로부터 메시지 수신"""
        data = await websocket.receive_json()
        return ClientMessage.model_validate(data)

    # 내부 구현 (private)
    async def _accept_connection(self, websocket: WebSocket) -> None:
        """웹소켓 연결 수락 (내부 메서드)"""
        await websocket.accept()

    async def _add_connection(self, websocket: WebSocket) -> None:
        """활성 연결 목록에 추가 (내부 메서드)"""
        async with self.lock:
            self.active_connections.add(websocket)

    async def _remove_connection(self, websocket: WebSocket) -> None:
        """활성 연결 목록에서 제거 (내부 메서드)"""
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def _close_connection(self, websocket: WebSocket) -> None:
        await websocket.close()

    async def _get_active_connections(self) -> Set[WebSocket]:
        """활성 연결 목록의 안전한 복사본 반환 (내부 메서드)"""
        async with self.lock:
            return self.active_connections.copy()


def get_websocket_service() -> WebsocketService:
    return WebsocketService()
