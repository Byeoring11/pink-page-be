import asyncio
import json
from fastapi import WebSocket
from typing import Optional, Tuple
from app.core.websocket import task_state_manager
from app.schemas.deud_ws import (
    WebSocketMessage,
    TaskStartMessage, TaskLogMessage, TaskCompleteMessage,
    TaskErrorMessage, TaskCancelledMessage, TaskStateUpdateMessage,
    ClientMessage
)
from app.core.logger import logger
# from app.core.exceptions import TaskAlreadyRunningError


class WebSocketService:
    @staticmethod
    async def send_message(websocket: WebSocket, message: WebSocketMessage) -> None:
        """Send a message to the websocket client."""
        try:
            await websocket.send_text(json.dumps(message.model_dump()))
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise

    @staticmethod
    async def handle_client_connection(websocket: WebSocket) -> None:
        """Handle the initial client connection."""
        await websocket.accept()

        # Add the connection to the state manager
        async with task_state_manager.lock:
            await task_state_manager.add_connection(websocket)

        # Send initial state
        state_message = TaskStateUpdateMessage(state=task_state_manager.task_state)
        await WebSocketService.send_message(websocket, state_message)

    @staticmethod
    async def handle_client_disconnection(websocket: WebSocket, current_task: Optional[asyncio.Task] = None) -> None:
        """Handle client disconnection logic."""
        logger.info('WebSocket connection closed')

        # Clean up on disconnect
        if current_task is not None and not current_task.done():
            current_task.cancel()

        async with task_state_manager.lock:
            await task_state_manager.remove_connection(websocket)

            # Reset state if this connection was the task owner
            if task_state_manager.is_task_running() and task_state_manager.is_task_owner(websocket):
                await task_state_manager.update_state(True)
                await task_state_manager.set_task_owner(None)

    @staticmethod
    async def process_client_message(
        websocket: WebSocket,
        message_data: str,
        current_task: Optional[asyncio.Task]
    ) -> Tuple[Optional[asyncio.Task], bool]:
        """Process incoming client message and return updated task and continue flag."""
        try:
            msg = json.loads(message_data)
            client_message = ClientMessage(**msg)
            logger.info(f"Received message: {client_message.model_dump()}")

            if client_message.action == "start_task":
                return await WebSocketService._handle_start_task(websocket, client_message, current_task)

            elif client_message.action == "task_cancel":
                return await WebSocketService._handle_cancel_task(websocket, client_message, current_task)

            return current_task, True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {str(e)}")
            error_msg = TaskErrorMessage(serverType=client_message.serverType, message="Invalid JSON format")
            await WebSocketService.send_message(websocket, error_msg)
            return current_task, True

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            error_msg = TaskErrorMessage(serverType=0, message=f"Error processing message: {str(e)}")
            await WebSocketService.send_message(websocket, error_msg)
            return current_task, True

    @staticmethod
    async def _handle_start_task(
        websocket: WebSocket,
        client_message: ClientMessage,
        current_task: Optional[asyncio.Task]
    ) -> Tuple[Optional[asyncio.Task], bool]:
        """Handle start_task action from client."""
        server_type = client_message.serverType
        if server_type is None:
            error_msg = TaskErrorMessage(serverType=0, message="Server type is required")
            await WebSocketService.send_message(websocket, error_msg)
            return current_task, True

        # Handle server type 1 special case
        if server_type == 1:
            async with task_state_manager.lock:
                if task_state_manager.is_task_running():
                    error_msg = TaskErrorMessage(serverType=server_type, message='Task already running')
                    await WebSocketService.send_message(websocket, error_msg)
                    return current_task, True

                await task_state_manager.update_state(False)
                await task_state_manager.set_task_owner(websocket)

        # Start new task if no task is running
        if current_task is None or current_task.done():
            logger.info(f"Creating new task with server_type: {server_type}")
            new_task = asyncio.create_task(TaskService.handle_task(websocket, server_type))
            return new_task, True
        else:
            error_msg = TaskErrorMessage(serverType=server_type, message='Task already running')
            await WebSocketService.send_message(websocket, error_msg)
            return current_task, True

    @staticmethod
    async def _handle_cancel_task(
        websocket: WebSocket,
        client_message: ClientMessage,
        current_task: Optional[asyncio.Task]
    ) -> Tuple[Optional[asyncio.Task], bool]:
        """Handle task_cancel action from client."""
        server_type = client_message.serverType
        if server_type is None:
            error_msg = TaskErrorMessage(serverType=0, message="Server type is required")
            await WebSocketService.send_message(websocket, error_msg)
            return current_task, True

        # Cancel the task if it's running
        if current_task is not None and not current_task.done():
            current_task.cancel()

            cancel_msg = TaskCancelledMessage(serverType=server_type, message='Task cancelled')
            await WebSocketService.send_message(websocket, cancel_msg)

            # Reset state after cancellation
            async with task_state_manager.lock:
                await task_state_manager.update_state(True)
                await task_state_manager.set_task_owner(None)

            return current_task, True

        return current_task, True


class TaskService:
    @staticmethod
    async def handle_task(websocket: WebSocket, server_type: int) -> None:
        """Handle a task with the given server type."""
        try:
            logger.info(f"Starting task with server_type: {server_type}")

            # Send task start notification
            start_message = TaskStartMessage(serverType=server_type)
            await WebSocketService.send_message(websocket, start_message)

            # Simulate a task with 3 iterations
            await TaskService._run_task_iterations(websocket, server_type)

            # Reset state if server_type is 3
            if server_type == 3:
                await TaskService._reset_task_state()

            # Send completion message
            complete_message = TaskCompleteMessage(serverType=server_type)
            await WebSocketService.send_message(websocket, complete_message)

        except asyncio.CancelledError:
            logger.warning(f"Task with server_type {server_type} was cancelled")
            raise

        except Exception as e:
            logger.error(f"Error in task with server_type {server_type}: {str(e)}")

            try:
                error_message = TaskErrorMessage(serverType=server_type, message=str(e))
                await WebSocketService.send_message(websocket, error_message)
            except Exception as send_error:
                logger.error(f"Error sending error message: {str(send_error)}")

            raise

    @staticmethod
    async def _run_task_iterations(websocket: WebSocket, server_type: int) -> None:
        """Run task iterations with logs sent to client."""
        for i in range(3):
            await asyncio.sleep(1)
            logger.info(f"Task iteration for server_type {server_type}: {i + 1}")

            log_message = TaskLogMessage(serverType=server_type, value=i + 1)
            await WebSocketService.send_message(websocket, log_message)

    @staticmethod
    async def _reset_task_state() -> None:
        """Reset task state to available."""
        async with task_state_manager.lock:
            await task_state_manager.update_state(True)
            await task_state_manager.set_task_owner(None)
