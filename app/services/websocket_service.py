from typing import Set
from fastapi import WebSocket
from app.schemas.websocket import WebSocketMessage, ClientMessage


class WebsocketService:
    @staticmethod
    async def accept_connection(websocket: WebSocket) -> None:
        await websocket.accept()

    @staticmethod
    async def send_message(websocket: WebSocket, message: WebSocketMessage) -> None:
        await websocket.send_json(message)

    @staticmethod
    async def receive_message(websocket: WebSocket) -> ClientMessage:
        return await websocket.receive_json()


class WebsocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def add_connection(self, websocket: WebSocket):
        self.active_connections.add(websocket)

    async def remove_connection(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


websocket_service = WebsocketService()
websocket_manager = WebsocketManager()
