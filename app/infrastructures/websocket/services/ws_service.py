from typing import Dict, Any, Optional, Callable, Awaitable
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logger import logger
from app.infrastructures.websocket.interfaces import WebSocketConnectionManagerInterface, WebSocketEventHandlerInterface
from app.infrastructures.websocket.implements import ConnectionManager, WebSocketEventHandler, RoomManager


class WebSocketService:
    """WebSocket 서비스 구현"""

    def __init__(
        self,
        connection_manager: Optional[WebSocketConnectionManagerInterface] = None,
        event_handler: Optional[WebSocketEventHandlerInterface] = None,
        room_manager: Optional[RoomManager] = None
    ):
        self.connection_manager = connection_manager or ConnectionManager()
        self.event_handler = event_handler or WebSocketEventHandler()
        self.room_manager = room_manager or RoomManager(self.connection_manager)

    async def handle_websocket(
        self,
        websocket: WebSocket,
        client_id: Optional[str] = None,
        on_connect: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        on_disconnect: Optional[Callable[[str], Awaitable[None]]] = None,
        on_message: Optional[Callable[[str, Any], Awaitable[None]]] = None,
        client_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """WebSocket 연결 처리"""
        # 클라이언트 ID가 없으면 자동 생성
        if not client_id:
            client_id = str(uuid.uuid4())

        try:
            # 연결 수락
            await self.connection_manager.connect(websocket, client_id, client_metadata)

            # 연결 이벤트 처리
            if on_connect:
                await on_connect(client_id, client_metadata or {})

            # 메시지 수신 루프
            while True:
                try:
                    message = await self.connection_manager.receive_message(client_id)

                    if isinstance(message, dict) and "event" in message:
                        event_name = message["event"]
                        event_data = message.get("data", {})
                        await self.event_handler.handle_event(event_name, event_data)

                    if on_message:
                        await on_message(client_id, message)

                except WebSocketDisconnect:
                    break

        except WebSocketDisconnect:
            logger.info(f"클라이언트 '{client_id}'의 연결이 해제되었습니다.")
        except Exception as e:
            logger.error(f"웹소켓 연결 오류 발생 {str(e)}")
        finally:
            # 연결 종료 시 정리
            await self.connection_manager.disconnect(client_id)
            self.room_manager.clean_client_connections(client_id)

            # 연결 종료 이벤트 처리
            if on_disconnect:
                await on_disconnect(client_id)
