import asyncio
from typing import Dict, List, Set, Optional, Any
from app.infrastructures.websocket.interfaces.connection_manager import WebSocketConnectionManagerInterface


class Room:
    """WebSocket 룸 클래스"""

    def __init__(self, room_id: str, name: Optional[str] = None):
        self.id = room_id
        self.name = name or room_id
        self.clients: Set[str] = set()
        self.metadata: Dict[str, Any] = {}

    def add_client(self, client_id: str) -> None:
        """룸에 클라이언트 추가"""
        self.clients.add(client_id)

    def remove_client(self, client_id: str) -> None:
        """룸에서 클라이언트 제거"""
        if client_id in self.clients:
            self.clients.remove(client_id)

    def get_clients(self) -> List[str]:
        """룸에 있는 모든 클라이언트 ID 반환"""
        return list(self.clients)

    def is_empty(self) -> bool:
        """룸이 비어있는지 확인"""
        return len(self.clients) == 0


class RoomManager:
    """WebSocket 룸 관리자 클래스"""

    def __init__(self, connection_manager: WebSocketConnectionManagerInterface):
        self.rooms: Dict[str, Room] = {}
        self.connection_manager = connection_manager
        self.client_rooms: Dict[str, Set[str]] = {}  # 클라이언트가 어떤 룸에 있는지 추적
        self.lock = asyncio.Lock()

    async def create_room(self, room_id: str, name: Optional[str] = None) -> Room:
        """새로운 룸 생성"""
        async with self.lock:
            if room_id in self.rooms:
                return self.rooms[room_id]

            room = Room(room_id, name)
            self.rooms[room_id] = room
            return room

    async def get_room(self, room_id: str) -> Optional[Room]:
        """룸 ID로 룸 가져오기"""
        async with self.lock:
            return self.rooms.get(room_id)

    async def delete_room(self, room_id: str) -> bool:
        """룸 삭제"""
        async with self.lock:
            if room_id in self.rooms:
                room = self.rooms[room_id]
                # 모든 클라이언트의 룸 정보 업데이트
                for client_id in room.get_clients():
                    if client_id in self.client_rooms and room_id in self.client_rooms[client_id]:
                        self.client_rooms[client_id].remove(room_id)

                del self.rooms[room_id]
                return True
            return False

    async def join_room(self, client_id: str, room_id: str) -> None:
        """클라이언트를 룸에 추가"""
        async with self.lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = Room(room_id)

            room = self.rooms[room_id]
            room.add_client(client_id)

            if client_id not in self.client_rooms:
                self.client_rooms[client_id] = set()

            self.client_rooms[client_id].add(room_id)

    async def leave_room(self, client_id: str, room_id: str) -> None:
        """클라이언트를 룸에서 제거"""
        async with self.lock:
            if room_id in self.rooms:
                room = self.rooms[room_id]
                room.remove_client(client_id)

                if client_id in self.client_rooms and room_id in self.client_rooms[client_id]:
                    self.client_rooms[client_id].remove(room_id)

                # 룸이 비어있으면 삭제 고려
                if room.is_empty():
                    del self.rooms[room_id]

    def get_client_rooms(self, client_id: str) -> List[str]:
        """클라이언트가 속한 모든 룸 ID 반환"""
        return list(self.client_rooms.get(client_id, set()))

    async def broadcast_to_room(self, room_id: str, message: Any, exclude: Optional[List[str]] = None) -> None:
        """특정 룸의 모든 클라이언트에게 메시지 브로드캐스트"""
        if room_id not in self.rooms:
            return

        room = self.rooms[room_id]
        clients_to_send = room.get_clients()
        exclude_set = set(exclude or [])

        for client_id in clients_to_send:
            if client_id not in exclude_set:
                try:
                    await self.connection_manager.send_message(client_id, message)
                except Exception:
                    # 연결이 끊긴 클라이언트는 룸에서 제거
                    self.leave_room(client_id, room_id)

    def clean_client_connections(self, client_id: str) -> None:
        """클라이언트 연결이 끊어졌을 때 모든 룸에서 제거"""
        if client_id in self.client_rooms:
            room_ids = list(self.client_rooms[client_id])
            for room_id in room_ids:
                self.leave_room(client_id, room_id)
            del self.client_rooms[client_id]
