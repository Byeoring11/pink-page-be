import asyncio
from typing import Set, Dict, Optional, Any, Type, TypeVar, Callable, List
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.infrastructures.websocket.schemas.websocket import WebSocketMessage, ClientMessage
from app.core.logger import logger

T = TypeVar('T', bound=BaseModel)


class WebSocketService:
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # 연결 관리 API
    async def connect(self, websocket: WebSocket) -> None:
        """웹소켓 연결 수락 및 등록"""
        try:
            await websocket.accept()
            async with self._lock:
                self._active_connections.add(websocket)
                self._metadata[websocket] = {}
            logger.info(f"[websocket_service] 웹소켓 연결 성공: {id(websocket)}")
        except Exception as e:
            logger.error(f"[websocket_service] 웹소켓 연결 실패: {str(e)}")
            raise WebSocketConnectionError(f"웹소켓 연결 실패: {str(e)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """웹소켓 연결 해제 및 등록 취소"""
        try:
            async with self._lock:
                if websocket in self._active_connections:
                    self._active_connections.remove(websocket)
                    logger.info(f"[websocket_service] 활성 연결 목록에서 웹소켓 제거: {id(websocket)}")

                if websocket in self._metadata:
                    del self._metadata[websocket]
                    logger.info(f"[websocket_service] 웹소켓 메타데이터 제거: {id(websocket)}")
        except Exception as e:
            logger.error(f"웹소켓 연결 해제 실패: {str(e)}")

    # 메시지 전송 API
    async def send_message(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        """단일 클라이언트에 메시지 전송"""
        if websocket not in self._active_connections:
            logger.warning(f"[websocket_service] 활성 연결 목록에 없는 웹소켓에 메시지 전송 시도 탐지: {id(websocket)}")
            return

        try:
            message_data = message.model_dump()
            await websocket.send_json(message_data)
            logger.info(f"[websocket_service] 웹소켓 메세지 전송 성공 {id(websocket)}: {message.type}")
            logger.debug(f"메세지 상세: {message_data}")
        except WebSocketDisconnect:
            logger.warning(f"[websocket_service] 메세지 전송 중 클라이언트 연결 해제: {id(websocket)}")
            await self.disconnect(websocket)
        except Exception as e:
            logger.error(f"[websocket_service] 웹소켓 메세지 전송 실패 {id(websocket)}: {str(e)}")
            raise WebSocketMessageError(f"웹소켓 메세지 전송 실패: {str(e)}")

    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude: Optional[WebSocket] = None
    ) -> None:
        """
        모든 활성 클라이언트에 메시지 브로드캐스트
        
        Args:
            message: 전송할 메시지
            exclude: 제외할 웹소켓 연결
            filter_func: 필터링 함수. True 반환시에만 메시지 전송
        """
        connections = await self._get_active_connections()
        logger.info(f"[websocket_service] 웹소켓 메세지 브로드캐스팅 - type '{message.type}' to {len(connections)} clients")

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
            receive_data = await websocket.receive_json()
            logger.info(f"[websocket_service] 웹소켓 메세지 수신 성공 {id(websocket)}: {receive_data}")

            validated_message = model_type.model_validate(receive_data)            
            if model_type == ClientMessage and hasattr(validated_message, 'action'):
                logger.info(f"[websocket_service] 수신 웹소켓 메세지 유효성 검증 성공")

            return validated_message
        except WebSocketDisconnect:
            logger.warning(f"[websocket_service] 메세지 수신 중 클라이언트 연결 해제: {id(websocket)}")
            await self.disconnect(websocket)
            raise
        except ValueError as e:
            logger.error(f"[websocket_service] 웹소켓 수신 메세지 값 검증 실패 {id(websocket)}: {str(e)}")
            raise WebSocketMessageError(f"웹소켓 수신 메세지 값 검증 실패: {str(e)}")
        except Exception as e:
            logger.error(f"[websocket_service] 웹소켓 메세지 수신 실패 {id(websocket)}: {str(e)}")
            raise WebSocketMessageError(f"웹소켓 메세지 수신 실패: {str(e)}")

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
