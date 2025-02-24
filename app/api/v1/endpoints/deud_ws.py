from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
import asyncio
from app.services.deud_ws import WebSocketService
from app.core.logger import logger

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Initialize connection
    await WebSocketService.handle_client_connection(websocket)
    current_task: Optional[asyncio.Task] = None

    try:
        # Main message handling loop
        while True:
            data = await websocket.receive_text()
            current_task, should_continue = await WebSocketService.process_client_message(
                websocket, data, current_task
            )

            if not should_continue:
                break

    except WebSocketDisconnect:
        # Handle disconnection
        await WebSocketService.handle_client_disconnection(websocket, current_task)

    except Exception as e:
        logger.error(f"Unhandled exception in websocket endpoint: {str(e)}")

        # Clean up on error
        if current_task is not None and not current_task.done():
            current_task.cancel()

        # Try to close the connection if it's still open
        try:
            await websocket.close()
        except Exception:
            pass
