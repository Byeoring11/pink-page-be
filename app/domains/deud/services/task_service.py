import asyncio
from typing import Optional, Any
from fastapi import WebSocket, Depends

from app.domains.deud.schema import TaskStateUpdateMessage, TaskErrorMessage, TaskCancelledMessage
from app.services.websocket_service import WebsocketService, get_websocket_service
from app.core.logger import logger


class TaskStateManager:
    """작업 상태 및 소유권 관리를 위한 클래스"""
    def __init__(self, websocket_manager: WebsocketService):
        self._lock = asyncio.Lock()
        self._task_available = True
        self._task_owner: Optional[WebSocket] = None
        self._websocket_manager = websocket_manager

    @property
    def is_task_available(self) -> bool:
        """현재 작업 수락 가능 여부"""
        return self._task_available

    async def acquire_task_ownership(self, websocket: WebSocket) -> bool:
        """작업 소유권 획득 시도"""
        async with self._lock:
            if self._task_available and self._task_owner is None:
                self._task_owner = websocket
                self._task_available = False
                await self._websocket_manager.broadcast(
                    TaskStateUpdateMessage(state=False),
                    exclude=websocket
                )
                return True
            return False

    async def release_task_ownership(self, websocket: WebSocket) -> None:
        """작업 소유권 해제"""
        async with self._lock:
            if self._task_owner == websocket:
                self._task_owner = None
                self._task_available = True
                await self._websocket_manager.broadcast(
                    TaskStateUpdateMessage(state=True)
                )

    async def validate_ownership(self, websocket: WebSocket) -> bool:
        """소유권 유효성 검증"""
        async with self._lock:
            return self._task_owner == websocket

    async def handle_owner_disconnect(self, websocket: WebSocket) -> None:
        """소유자 연결 종료 시 처리"""
        async with self._lock:
            if self._task_owner == websocket:
                logger.info(f"Owner disconnected: {websocket}")
                await self.release_task_ownership(websocket)

    async def send_task_unavailable_message(self, websocket: WebSocket, server_type: int) -> None:
        async with self._lock:
            error_msg = TaskErrorMessage(serverType=server_type, message="Task already running")
            await self._websocket_manager.send_message(websocket, error_msg)

    async def send_task_cancelled_message(self, websocket: WebSocket, server_type: int) -> None:
        async with self._lock:
            cancel_msg = TaskCancelledMessage(serverType=server_type, message="Task cancelled")
            await self._websocket_manager.send_message(websocket, cancel_msg)


class TaskManager:
    """비동기 작업 실행 관리 클래스"""
    def __init__(self):
        self._current_task: Optional[asyncio.Task] = None
        self._task_lock = asyncio.Lock()

    @property
    def is_task_running(self) -> bool:
        """작업 실행 중 여부 확인"""
        return self._current_task is not None and not self._current_task.done()

    async def start_task(self, task_func: Any, *args, **kwargs) -> None:
        """새 작업 시작"""
        async with self._task_lock:
            if self.is_task_running:
                raise RuntimeError("Task is already running")
            self._current_task = asyncio.create_task(task_func(*args, **kwargs))

    async def cancel_current_task(self) -> None:
        """현재 작업 취소"""
        async with self._task_lock:
            if self.is_task_running:
                self._current_task.cancel()
                try:
                    await self._current_task
                except asyncio.CancelledError:
                    logger.info("Task cancelled successfully")


# 의존성 주입 설정
def get_task_state_manager(
    websocket_service: WebsocketService = Depends(get_websocket_service)
) -> TaskStateManager:
    return TaskStateManager(websocket_service)


def get_task_manager() -> TaskManager:
    return TaskManager()
