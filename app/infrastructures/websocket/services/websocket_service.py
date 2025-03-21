import asyncio
from typing import Set, Dict, Optional, Any, Type, TypeVar
from fastapi import WebSocket
from pydantic import BaseModel

from app.infrastructures.websocket.schemas.websocket import WebSocketMessage, ClientMessage
from app.core.logger import logger

T = TypeVar('T', bound=BaseModel)


class WebSocketService:
    """
    웹소켓 서비스

    웹소켓 연결 및 메시지 처리를 담당하는 서비스
    """
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # 연결 관리 API
    async def connect(self, websocket: WebSocket) -> None:
        """웹소켓 연결 수락 및 등록"""
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
            self._metadata[websocket] = {}
        logger.info(f"WebSocket client connected: {id(websocket)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """웹소켓 연결 해제 및 등록 취소"""
        async with self._lock:
            if websocket in self._active_connections:
                self._active_connections.remove(websocket)

            if websocket in self._metadata:
                del self._metadata[websocket]

        logger.info(f"WebSocket client disconnected: {id(websocket)}")

    # 메시지 전송 API
    async def send_message(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        """단일 클라이언트에 메시지 전송"""
        try:
            await websocket.send_json(message.model_dump())
            logger.info(f"Success sending message to client {id(websocket)}: {message.model_dump()}")
        except Exception as e:
            logger.error(f"Failed to send message to client {id(websocket)}: {str(e)}")

    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude: Optional[WebSocket] = None
    ) -> None:
        """모든 활성 클라이언트에 메시지 브로드캐스트"""
        connections = await self._get_active_connections()

        # 각 클라이언트 별 전송 작업 생성
        tasks = []
        for connection in connections:
            if connection != exclude:
                tasks.append(self.send_message(connection, message))

        # 병렬 전송 실행 (실패 허용)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # 메시지 수신 API
    async def receive_message(self, websocket: WebSocket, model_type: Type[T] = ClientMessage) -> T:
        """클라이언트로부터 메시지 수신 및 검증"""
        try:
            data = await websocket.receive_json()
            return ClientMessage.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to receive/parse message from client {id(websocket)}: {str(e)}")
            raise

    # 메타데이터 API
    async def set_metadata(self, websocket: WebSocket, key: str, value: Any) -> None:
        """웹소켓 연결에 메타데이터 설정"""
        async with self._lock:
            if websocket in self._metadata:
                self._metadata[websocket][key] = value

    async def get_metadata(self, websocket: WebSocket, key: str, default: Any = None) -> Any:
        """웹소켓 연결의 메타데이터 조회"""
        async with self._lock:
            if websocket in self._metadata and key in self._metadata[websocket]:
                return self._metadata[websocket][key]
            return default

    # 내부 유틸리티
    async def _get_active_connections(self) -> Set[WebSocket]:
        """활성 연결 목록의 안전한 복사본 반환"""
        async with self._lock:
            return self._active_connections.copy()
