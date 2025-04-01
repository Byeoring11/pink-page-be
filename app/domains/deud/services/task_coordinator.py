import asyncio
from typing import List
from fastapi import WebSocket

from app.domains.deud.schemas.websocket_task_schema import TaskCompleteMessage, TaskStartMessage
from app.domains.deud.services.task_manager import TaskManager
from app.domains.deud.services.ssh_service import DeudSSHService
from app.infrastructures.websocket.services.websocket_service import WebSocketService
from app.core.logger import logger


class TaskCoordinator:
    """
    작업 조정자

    웹소켓 요청과 작업 관리자 간의 중재자 역할
    클라이언트 명령어 해석 및 적절한 작업 실행 조정
    """
    def __init__(self, websocket_service: WebSocketService, task_manager: TaskManager):
        self._websocket_service = websocket_service
        self._task_manager = task_manager

    async def inform_task_state(self, websocket: WebSocket) -> None:
        await self._task_manager.send_inform_state_message(websocket)

    async def process_start_request(
        self,
        websocket: WebSocket,
        server_type: int,
        cusno_list: List[str]
    ) -> bool:
        """
        작업 시작 요청 처리

        Parameters:
        - websocket: 요청한 웹소켓 클라이언트
        - server_type: 서버 유형 식별자
        - cusno_list: 처리할 고객 번호 목록

        Returns:
        - 작업 시작 성공 여부
        """
        # 작업 가능 상태 확인
        if self._task_manager.is_running and not await self._task_manager.validate_ownership(websocket):
            logger.info(f"Task unavailable. Request rejected for client: {id(websocket)}")
            await self._task_manager.send_error_message(
                websocket,
                server_type,
                "Task already running or unavailable"
            )
            return False

        # 서버 타입에 따른 작업 소유권 획득 (예: 타입 1만 소유권 필요)
        if server_type == 1:
            ownership_acquired = await self._task_manager.acquire_ownership(websocket)
            if not ownership_acquired:
                logger.info(f"Failed to acquire task ownership for client: {id(websocket)}")
                return False

        # 작업 시작
        task_start_message = TaskStartMessage(serverType=server_type)
        await self._websocket_service.send_message(websocket, task_start_message)
        logger.info(f"Starting task for server_type {server_type} with {cusno_list}")

        success = await self._task_manager.start_task(
            websocket,
            self._execute_task,
            websocket,
            server_type,
            cusno_list
        )

        return success

    async def process_cancel_request(
        self,
        websocket: WebSocket,
        server_type: int
    ) -> bool:
        """
        작업 취소 요청 처리

        Parameters:
        - websocket: 요청한 웹소켓 클라이언트
        - server_type: 서버 유형 식별자

        Returns:
        - 작업 취소 성공 여부
        """
        # 작업 취소 시도
        success = await self._task_manager.cancel_task(websocket)

        if success:
            # 취소 메시지 전송
            await self._task_manager.send_cancelled_message(websocket, server_type)

            # 작업 소유권 해제
            await self._task_manager.release_ownership(websocket)

            logger.info(f"Task cancelled by client: {id(websocket)}")

        return success

    async def handle_client_disconnect(self, websocket: WebSocket) -> None:
        """클라이언트 연결 해제 처리"""
        await self._task_manager.handle_client_disconnect(websocket)

    # 내부 작업 실행 메서드
    async def _execute_task(
        self,
        websocket: WebSocket,
        server_type: int,
        cusno_list: List[str]
    ) -> None:
        """
        실제 작업 실행 로직
        """
        try:
            logger.info(f"Executing task for server_type: {server_type}")
            #########################################################################################
            # 테스트 로직 START
            #########################################################################################
            from app.domains.deud.services.mock_service import MockService
            mock_service = MockService(self._websocket_service)
            await mock_service.iterate_with_sleep(websocket, server_type, cusno_list)
            #########################################################################################
            # 테스트 로직 END
            #########################################################################################
            # deud_ssh_service = DeudSSHService(self._websocket_service)
            # await deud_ssh_service.execute_shell_controller(websocket, server_type, cusno_list)

            # 작업 완료 메시지 전송
            complete_message = TaskCompleteMessage(serverType=server_type)
            await self._websocket_service.send_message(websocket, complete_message)

            logger.info(f"Task completed for server_type: {server_type}")

            # 마지막 서버였으면 작업 소유권 반환
            if server_type == 3:
                await self._task_manager.release_ownership(websocket)

        except asyncio.CancelledError:
            logger.info(f"Task execution cancelled for server_type: {server_type}")

            raise
        except Exception as e:
            logger.error(f"Error in task execution for server_type {server_type}: {str(e)}")
            raise
