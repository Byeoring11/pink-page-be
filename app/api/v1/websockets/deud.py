from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect

from app.domains.deud.services.task_service import (
    TaskManager, TaskStateManager, get_task_manager, get_task_state_manager
)
from app.domains.deud.services.mock_service import MockService, get_mock_service
from app.services.websocket_service import WebsocketService, get_websocket_service
from app.schemas.websocket import ClientMessage
from app.core.logger import logger

router = APIRouter()


@router.websocket("/deud")
async def websocket_endpoint(
    websocket: WebSocket,
    websocket_service: WebsocketService = Depends(get_websocket_service),
    task_manager: TaskManager = Depends(get_task_manager),
    task_state_manager: TaskStateManager = Depends(get_task_state_manager),
    mock_service: MockService = Depends(get_mock_service)
):
    websocket_service.connect(websocket)

    try:
        while True:
            client_message: ClientMessage = await websocket_service.receive_message(websocket)
            if client_message.action == "start_task":
                if not task_state_manager.is_task_available:
                    await task_state_manager.send_task_unavailable_message(websocket, client_message.serverType)
                    continue

                if client_message.serverType == 1:
                    await task_state_manager.acquire_task_ownership(websocket)

                await task_manager.start_task(
                    mock_service.iterate_with_sleep(websocket, client_message.serverType, client_message.cusnoList)
                )

            elif client_message.action == "task_cancel":
                await task_manager.cancel_current_task()
                await task_state_manager.send_task_cancelled_message(websocket, client_message.serverType)
                await task_state_manager.release_task_ownership(websocket)

    except WebSocketDisconnect:
        if task_manager.is_task_running:
            await task_manager.cancel_current_task()

        await websocket_service.disconnect(websocket)

    except Exception as e:
        logger.error(f"Unhandled exception in websocket endpoint: {str(e)}")

        if task_manager.is_task_running:
            await task_manager.cancel_current_task()
