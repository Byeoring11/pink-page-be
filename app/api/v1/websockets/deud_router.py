from fastapi import APIRouter, WebSocket, Depends
from typing import Dict, Any
from app.infrastructures.websocket.dependencies import get_websocket_service
from app.infrastructures.websocket.services import WebSocketService

router = APIRouter()


# 채팅방 이벤트 핸들러 등록
# @websocket_service.event_handler.register_event_handler("join_room")
# async def handle_join_room(data: Dict[str, Any]):
#     client_id = data.get("client_id")
#     room_id = data.get("room_id")
#     if client_id and room_id:
#         await websocket_service.room_manager.join_room(client_id, room_id)
#         await websocket_service.room_manager.broadcast_to_room(
#             room_id,
#             {"event": "user_joined", "data": {"client_id": client_id}},
#             exclude=[client_id]
#         )


@router.websocket("/chat/{client_id}")
async def deud_websocket(
    websocket: WebSocket,
    websocket_service: WebSocketService = Depends(get_websocket_service)
):
    """대응답 WebSocket 엔드포인트"""

    async def on_connect(client_id: str, metadata: Dict[str, Any]):
        """클라이언트 연결 시 실행되는 콜백"""
        print(f"Client {client_id} connected with metadata: {metadata}")

    async def on_disconnect(client_id: str):
        """클라이언트 연결 해제 시 실행되는 콜백"""
        print(f"Client {client_id} disconnected")

    async def on_message(client_id: str, message: Any):
        """메시지 수신 시 실행되는 콜백"""
        if isinstance(message, dict) and "room_id" in message:
            # 특정 룸에 메시지 전송
            room_id = message["room_id"]
            await websocket_service.room_manager.broadcast_to_room(
                room_id,
                {"event": "chat_message", "data": {"client_id": client_id, "message": message.get("message", "")}},
                exclude=[] if message.get("include_self", False) else [client_id]
            )

    # 클라이언트 IP
    client_id = websocket.client.host

    # WebSocket 연결 처리
    await websocket_service.handle_websocket(
        websocket,
        client_id,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_message=on_message,
        client_metadata={"user_agent": websocket.headers.get("user-agent", "")}
    )
