import asyncio
from typing import Optional, Any, Callable, Awaitable
from fastapi import WebSocket

from app.domains.deud.schema import TaskStateUpdateMessage, TaskErrorMessage, TaskCancelledMessage
from app.services.websocket_service import WebSocketService
from app.core.logger import logger


class TaskManager:
    """
    통합 작업 관리자

    작업 상태, 소유권, 실행을 단일 클래스에서 관리
    """
    def __init__(self, websocket_service: WebSocketService):
        # 상태 관리 관련 속성
        self._state_lock = asyncio.Lock()
        self._available = True
        self._owner: Optional[WebSocket] = None

        # 작업 실행 관련 속성
        self._task_lock = asyncio.Lock()
        self._current_task: Optional[asyncio.Task] = None

        # 의존성
        self._websocket_service: WebSocketService = websocket_service

    # 상태 관리 API

    @property
    def is_available(self) -> bool:
        """작업 수락 가능 여부"""
        return self._available and not self.is_running

    @property
    def is_running(self) -> bool:
        """작업 실행 중 여부"""
        return self._current_task is not None and not self._current_task.done()

    async def acquire_ownership(self, websocket: WebSocket) -> bool:
        """작업 소유권 획득 시도"""
        async with self._state_lock:
            if not self.is_available:
                return False

            self._owner = websocket
            self._available = False

            # 다른 클라이언트들에게 상태 변경 알림
            await self._websocket_service.broadcast(
                TaskStateUpdateMessage(state=False),
                exclude=websocket
            )

            logger.info(f"Task ownership acquired by client: {id(websocket)}")
            return True

    async def release_ownership(self, websocket: WebSocket) -> None:
        """작업 소유권 해제"""
        async with self._state_lock:
            if self._owner != websocket:
                logger.warning(f"Unauthorized release attempt by client: {id(websocket)}")
                return

            self._owner = None
            self._available = True

            # 모든 클라이언트에게 상태 변경 알림
            await self._websocket_service.broadcast(
                TaskStateUpdateMessage(state=True)
            )

            logger.info(f"Task ownership released by client: {id(websocket)}")

    async def validate_ownership(self, websocket: WebSocket) -> bool:
        """소유권 유효성 검증"""
        return self._owner == websocket

    # 작업 실행 API

    async def start_task(
        self,
        owner: WebSocket,
        task_func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> bool:
        """
        새 작업 시작

        Parameters:
        - owner: 작업을 시작한 웹소켓 클라이언트
        - task_func: 실행할 비동기 함수
        - args, kwargs: 함수에 전달할 인수

        Returns:
        - 작업 시작 성공 여부
        """
        # 소유권 검증
        if not await self.validate_ownership(owner):
            logger.warning(f"Unauthorized task execution attempt by client: {id(owner)}")
            return False

        async with self._task_lock:
            if self.is_running:
                logger.warning("Task is already running, cannot start a new one")
                return False

            # 작업 실행
            async def _managed_task():
                try:
                    await task_func(*args, **kwargs)
                except asyncio.CancelledError:
                    logger.info("Task was cancelled")
                    raise
                except Exception as e:
                    logger.error(f"Task failed with error: {str(e)}")
                    raise
                finally:
                    # 작업 종료 시 소유권 자동 해제 (선택적)
                    # await self.release_ownership(owner)
                    pass

            self._current_task = asyncio.create_task(_managed_task())
            logger.info(f"Task started: {task_func.__name__}")
            return True

    async def cancel_task(self, requester: WebSocket) -> bool:
        """
        현재 실행 중인 작업 취소

        Parameters:
        - requester: 작업 취소를 요청한 웹소켓 클라이언트

        Returns:
        - 작업 취소 성공 여부
        """
        # 소유권 검증
        if not await self.validate_ownership(requester):
            logger.warning(f"Unauthorized task cancellation attempt by client: {id(requester)}")
            return False

        async with self._task_lock:
            if not self.is_running:
                logger.info("No task running to cancel")
                return False

            # 작업 취소
            self._current_task.cancel()

            try:
                await self._current_task
            except asyncio.CancelledError:
                logger.info("Task cancelled successfully")
            except Exception as e:
                logger.error(f"Error occurred during task cancellation: {str(e)}")

            return True

    # 클라이언트 상호작용 API
    async def send_error_message(self, websocket: WebSocket, server_type: int, message: str) -> None:
        """오류 메시지 전송"""
        error_msg = TaskErrorMessage(serverType=server_type, message=message)
        await self._websocket_service.send_message(websocket, error_msg)

    async def send_cancelled_message(self, websocket: WebSocket, server_type: int) -> None:
        """작업 취소 메시지 전송"""
        cancel_msg = TaskCancelledMessage(serverType=server_type, message="Task cancelled")
        await self._websocket_service.send_message(websocket, cancel_msg)

    # 클라이언트 연결 관리
    async def handle_client_disconnect(self, websocket: WebSocket) -> None:
        """클라이언트 연결 해제 처리"""
        if self._owner == websocket:
            logger.info(f"Task owner disconnected: {id(websocket)}")

            # 실행 중인 작업 취소
            if self.is_running:
                async with self._task_lock:
                    self._current_task.cancel()
                    try:
                        await self._current_task
                    except (asyncio.CancelledError, Exception):
                        pass

            # 소유권 해제
            await self.release_ownership(websocket)
