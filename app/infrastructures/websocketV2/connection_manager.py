import asyncio
import json
from typing import Dict, Any, Optional, Callable, Awaitable
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logger import logger
from app.core.exceptions import WSBroadcastException, ErrorCode


class WebSocketManager:
    """Low-level reusable WebSocket connection manager"""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, connection_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Accept WebSocket connection and store it"""
        await websocket.accept()

        async with self._lock:
            self.connections[connection_id] = websocket
            self.connection_metadata[connection_id] = metadata or {}

        logger.info(f"WebSocket connection established: {connection_id}")

    async def disconnect(self, connection_id: str) -> None:
        """Remove WebSocket connection"""
        async with self._lock:
            if connection_id in self.connections:
                del self.connections[connection_id]
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]

        logger.info(f"WebSocket connection removed: {connection_id}")

    async def send_text(self, connection_id: str, message: str) -> bool:
        """Send text message to specific connection"""
        if connection_id not in self.connections:
            logger.warning(f"Connection not found: {connection_id}")
            return False

        try:
            await self.connections[connection_id].send_text(message)
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            return False

    async def send_json(self, connection_id: str, data: Dict[str, Any]) -> bool:
        """특정 웹소켓 연결에게 json 형식의 메세지 발신"""
        if connection_id not in self.connections:
            logger.warning(f"Connection not found: {connection_id}")
            return False

        try:
            await self.connections[connection_id].send_json(data)
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending JSON to {connection_id}: {e}")
            return False

    async def send_bytes(self, connection_id: str, data: bytes) -> bool:
        """Send binary message to specific connection"""
        if connection_id not in self.connections:
            logger.warning(f"Connection not found: {connection_id}")
            return False

        try:
            await self.connections[connection_id].send_bytes(data)
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending bytes to {connection_id}: {e}")
            return False

    async def receive_message(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Receive message from specific connection"""
        if connection_id not in self.connections:
            return None

        try:
            message = await self.connections[connection_id].receive()

            if "text" in message:
                try:
                    return {"type": "json", "data": json.loads(message["text"])}
                except json.JSONDecodeError:
                    return {"type": "text", "data": message["text"]}
            elif "bytes" in message:
                return {"type": "bytes", "data": message["bytes"]}
            else:
                return {"type": "unknown", "data": message}

        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return None
        except Exception as e:
            logger.error(f"Error receiving message from {connection_id}: {e}")
            return None

    def is_connected(self, connection_id: str) -> bool:
        """Check if connection exists"""
        return connection_id in self.connections

    def get_metadata(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection metadata"""
        return self.connection_metadata.get(connection_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.connections)

    def get_connection_ids(self) -> list[str]:
        """Get all active connection IDs"""
        return list(self.connections.keys())

    async def broadcast_json(
        self,
        data: Dict[str, Any],
        exclude_ids: Optional[list[str]] = None,
        raise_on_failure: bool = False
    ) -> int:
        """
        모든 연결된 클라이언트에게 JSON 메시지를 브로드캐스트

        Args:
            data: 전송할 JSON 데이터
            exclude_ids: 제외할 connection_id 리스트 (선택사항)
            raise_on_failure: 실패 시 예외 발생 여부 (기본: False)

        Returns:
            성공적으로 전송된 클라이언트 수

        Raises:
            WSBroadcastException: raise_on_failure=True이고 전송 실패 시
        """
        exclude_ids = exclude_ids or []
        success_count = 0
        failed_connections = []

        async with self._lock:
            connection_ids = list(self.connections.keys())

        total_targets = len([cid for cid in connection_ids if cid not in exclude_ids])

        for connection_id in connection_ids:
            if connection_id in exclude_ids:
                continue

            if await self.send_json(connection_id, data):
                success_count += 1
            else:
                failed_connections.append(connection_id)

        # 에러 처리
        if failed_connections:
            logger.warning(
                f"Broadcast partially failed: {len(failed_connections)}/{total_targets} failed",
                extra={
                    "failed_connections": failed_connections,
                    "success_count": success_count,
                    "total_targets": total_targets
                }
            )

            if raise_on_failure:
                if success_count == 0:
                    # 모두 실패
                    raise WSBroadcastException(
                        total_connections=total_targets,
                        failed_connections=len(failed_connections),
                        detail=f"Broadcast failed to all {total_targets} connections",
                        error_code=ErrorCode.WS_BROADCAST_FAILED
                    )
                else:
                    # 부분 실패
                    raise WSBroadcastException(
                        total_connections=total_targets,
                        failed_connections=len(failed_connections),
                        detail=f"Broadcast partially failed: {len(failed_connections)}/{total_targets} connections failed",
                        error_code=ErrorCode.WS_BROADCAST_PARTIAL
                    )

        logger.info(f"Broadcast sent to {success_count}/{total_targets} connections")
        return success_count


class WebSocketHandler:
    """High-level WebSocket handler with event-based architecture"""

    def __init__(self, manager: WebSocketManager):
        self.manager = manager
        self.message_handlers: Dict[str, Callable] = {}
        self.connection_handlers: Dict[str, Callable] = {}

    def on_message(self, message_type: str):
        """Decorator to register message handlers"""
        def decorator(func: Callable[[str, Dict[str, Any]], Awaitable[None]]):
            self.message_handlers[message_type] = func
            return func
        return decorator

    def on_connect(self, event_name: str):
        """Decorator to register connection event handlers"""
        def decorator(func: Callable[[str], Awaitable[None]]):
            self.connection_handlers[event_name] = func
            return func
        return decorator

    async def handle_connection(self, websocket: WebSocket, connection_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Handle WebSocket connection lifecycle"""
        await self.manager.connect(websocket, connection_id, metadata)

        # Call connect handlers
        if "connect" in self.connection_handlers:
            await self.connection_handlers["connect"](connection_id)

        try:
            while True:
                message = await self.manager.receive_message(connection_id)
                if message is None:
                    break

                # Handle based on message type
                if message["type"] == "json" and isinstance(message["data"], dict):
                    msg_type = message["data"].get("type", "unknown")
                    if msg_type in self.message_handlers:
                        await self.message_handlers[msg_type](connection_id, message["data"])

        except Exception as e:
            logger.error(f"Error in WebSocket handler for {connection_id}: {e}")
        finally:
            await self.manager.disconnect(connection_id)
            # Call disconnect handlers
            if "disconnect" in self.connection_handlers:
                await self.connection_handlers["disconnect"](connection_id)
