import asyncio
import json
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.core.logger import logger
from app.infrastructures.websocket.interfaces import WebSocketConnectionManagerInterface
from app.infrastructures.websocket.exceptions.websocket_exceptions import ConnectionClosedException


class ConnectionManager(WebSocketConnectionManagerInterface):
    """WebSocket 연결 관리자 구현"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_info: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """클라이언트 연결을 수락하고 저장"""
        await websocket.accept()

        async with self.lock:  # lock을 사용하여 공유 자원 접근 보호
            self.active_connections[client_id] = websocket
            self.client_info[client_id] = metadata or {}

        logger.info(f"클라이언트 {client_id} 연결됨. 연결된 클라이언트 수: {len(self.active_connections)}")

    async def disconnect(self, client_id: str) -> None:
        """클라이언트 연결 해제"""
        async with self.lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                if client_id in self.client_info:
                    del self.client_info[client_id]
                logger.info(f"클라이언트 {client_id} 연결 해제됨. 연결된 클라이언트 수: {len(self.active_connections)}")

    async def send_message(self, client_id: str, message: Any) -> None:
        """특정 클라이언트에게 메시지 전송"""
        if client_id not in self.active_connections:
            raise ConnectionClosedException(f"연결 중이지 않은 클라이언트 {client_id}")

        websocket = self.active_connections[client_id]
        try:
            if isinstance(message, str):
                await websocket.send_text(message)
            elif isinstance(message, bytes):
                await websocket.send_bytes(message)
            elif isinstance(message, dict) or isinstance(message, list):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
            logger.info(f"웹소켓 메시지 전송 to 클라이언트 '{client_id}' - message: {message}")
        except WebSocketDisconnect:
            await self.disconnect(client_id)
            raise ConnectionClosedException(f"연결 해제된 클라이언트 {client_id}")

    async def broadcast(self, message: Any, exclude: Optional[List[str]] = None) -> None:
        """모든 클라이언트에게 메시지 병렬 브로드캐스트"""
        exclude_set = set(exclude or [])

        # 브로드캐스트할 클라이언트 필터링
        clients_to_send = [client_id for client_id in self.active_connections.keys() if client_id not in exclude_set]

        # 병렬로 메시지 전송
        send_tasks = []
        for client_id in clients_to_send:
            send_tasks.append(self._safe_send_message(client_id, message))

        # 모든 전송 작업 병렬 실행
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

    async def _safe_send_message(self, client_id: str, message: Any) -> None:
        """예외 처리가 포함된 안전한 메시지 전송 헬퍼 메서드"""
        try:
            await self.send_message(client_id, message)
        except ConnectionClosedException:
            # 이미 disconnect 메서드에서 처리됨
            pass
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {str(e)}")

    async def receive_message(self, client_id: str, timeout: Optional[float] = None) -> Any:
        """특정 클라이언트로부터 메시지 수신 (비동기적으로 대기)"""
        if client_id not in self.active_connections:
            raise ConnectionClosedException(f"연결 중이지 않은 클라이언트 {client_id}")

        websocket = self.active_connections[client_id]
        try:
            message = await websocket.receive()

            # 수신된 메시지 처리
            if "text" in message:
                data = message["text"]
                try:
                    # JSON 파싱 시도
                    json_data = json.loads(data)
                    logger.info(f"웹소켓 JSON 메시지 수신 from 클라이언트 '{client_id}'")
                    return json_data
                except json.JSONDecodeError:
                    # 일반 텍스트 메시지
                    logger.info(f"웹소켓 텍스트 메시지 수신 from 클라이언트 '{client_id}' - message: {data}")
                    return data
            elif "bytes" in message:
                # 바이너리 데이터
                binary_data = message["bytes"]
                logger.info(f"웹소켓 바이너리 메시지 수신 from 클라이언트 '{client_id}' - size: {len(binary_data)} bytes")
                return binary_data

            # 기타 메시지 타입
            logger.warning(f"처리되지 않은 웹소켓 메시지 타입 from 클라이언트 '{client_id}' - message: {message}")
            return message

        except WebSocketDisconnect:
            # 연결 해제 처리
            await self.disconnect(client_id)
            raise ConnectionClosedException(f"연결 해제된 클라이언트 {client_id}")
        except Exception as e:
            logger.error(f"메시지 수신 중 오류 발생 from 클라이언트 '{client_id}' - {str(e)}")
            raise

    def get_client_count(self) -> int:
        """연결된 클라이언트 수 반환"""
        return len(self.active_connections)

    def get_client_ids(self) -> List[str]:
        """연결된 모든 클라이언트 ID 반환"""
        return list(self.active_connections.keys())

    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """특정 클라이언트의 메타데이터 반환"""
        return self.client_info.get(client_id)
