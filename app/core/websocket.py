from fastapi import WebSocket
import json
import asyncio
from typing import Set, Optional


class TaskStateManager:
    def __init__(self):
        self.task_state = True
        self.lock = asyncio.Lock()
        self.connections: Set[WebSocket] = set()
        self.task_owner: Optional[WebSocket] = None

    async def add_connection(self, websocket: WebSocket) -> None:
        self.connections.add(websocket)

    async def remove_connection(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def set_task_owner(self, websocket: Optional[WebSocket]) -> None:
        self.task_owner = websocket

    async def update_state(self, new_state: bool) -> None:
        if self.task_state == new_state:
            return

        self.task_state = new_state
        await self.broadcast_state()

    async def broadcast_state(self) -> None:
        message = json.dumps({
            "type": "task_state_update",
            "state": self.task_state
        })

        for connection in self.connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Connection might be closed, skip it
                pass

    def is_task_running(self) -> bool:
        return not self.task_state

    def is_task_owner(self, websocket: WebSocket) -> bool:
        return websocket == self.task_owner


# Create a singleton instance
task_state_manager = TaskStateManager()
