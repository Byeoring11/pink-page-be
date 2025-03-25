import asyncio
from fastapi import WebSocket
from app.infrastructures.websocket.services.websocket_service import WebSocketService
from app.domains.deud.schemas.websocket_task_schema import TaskLogMessage
from app.core.logger import logger


class MockService:
    def __init__(self, websocket_service: WebSocketService):
        self._websocket_service = websocket_service

    async def iterate_with_sleep(self, websocket: WebSocket, server_type: int, cusno_list: list) -> None:
        total_iterations = 5

        for i in range(total_iterations):
            # 각 반복에서 취소 확인을 위한 중단점
            await asyncio.sleep(1)

            # 진행 상황 계산
            progress = (i + 1) / total_iterations * 100
            logger.info(f"Task progress for server_type {server_type}: {progress:.1f}%")

            # 클라이언트에게 진행 상황 보고
            log_message = TaskLogMessage(
                serverType=server_type,
                value={
                    "iteration": i + 1,
                    "progress": progress,
                    "cusnoCount": len(cusno_list),
                    "details": f"Processing batch {i + 1} of {total_iterations}"
                }
            )

            await self._websocket_service.send_message(websocket, log_message)
