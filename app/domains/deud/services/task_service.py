import asyncio
from typing import Optional
from fastapi import WebSocket

from app.domains.deud.schema import TaskStateUpdateMessage
from app.services.websocket_service import websocket_service, websocket_manager


class TaskStateManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.task_available_state: bool = True
        self.task_owner: Optional[WebSocket] = None

    async def set_task_owner(self, websocket: Optional[WebSocket]) -> None:
        self.task_owner = websocket

    async def update_task_available_state(self, new_state: bool) -> None:
        if self.task_available_state == new_state:
            return
        self.task_available_state = new_state
        await self.broadcast_state()

    async def broadcast_task_available_state(self) -> None:
        send_message = TaskStateUpdateMessage(state=self.task_available_state)
        for connection in websocket_manager.active_connections:
            await websocket_service.send_message(connection, send_message)

    async def is_task_running(self) -> bool:
        return not self.task_available_state

    async def is_task_owner(self, websocket: WebSocket) -> bool:
        return websocket == self.task_owner


task_state_manager = TaskStateManager()
