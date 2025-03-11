import asyncio
from fastapi import WebSocket, Depends
from app.services.websocket_service import WebsocketService, get_websocket_service
from app.domains.deud.schema import TaskLogMessage
from app.core.logger import logger


class MockService:
    def __init__(self, websocket_service: WebsocketService):
        self._websocket_service = websocket_service

    async def iterate_with_sleep(self, websocket: WebSocket, server_type: int, cusno_list: list) -> None:
        for i in range(3):
            await asyncio.sleep(1)
            logger.info(f"Task iteration for server_type {server_type}: {i + 1}")

            log_message = TaskLogMessage(serverType=server_type, value=i + 1)
            await self._websocket_service.send_message(websocket, log_message)


def get_mock_service(
    websocket_service: WebsocketService = Depends(get_websocket_service)
) -> MockService:
    return MockService(websocket_service)
