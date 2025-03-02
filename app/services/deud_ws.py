import asyncio
import json
import re
import paramiko
from fastapi import WebSocket
from typing import Optional, Tuple, List
from app.core.websocket import task_state_manager
from app.schemas.deud_ws import (
    WebSocketMessage,
    TaskStartMessage, TaskLogMessage, TaskCompleteMessage,
    TaskErrorMessage, TaskCancelledMessage, TaskStateUpdateMessage,
    ClientMessage
)
from app.core.logger import logger
from app.core.config import settings
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
        cusno_list = client_message.cusnoList

        if server_type is None:
            error_msg = TaskErrorMessage(serverType=0, message="Server type is required")
            await WebSocketService.send_message(websocket, error_msg)
            return current_task, True
        elif cusno_list is None:
            error_msg = TaskErrorMessage(serverType=0, message="Cusno list is required")
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
            new_task = asyncio.create_task(TaskService.handle_task(websocket, server_type, cusno_list))
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
    async def handle_task(websocket: WebSocket, server_type: int, cusno_list: List) -> None:
        """Handle a task with the given server type."""
        try:
            logger.info(f"Starting task with server_type: {server_type}")

            # Send task start notification
            start_message = TaskStartMessage(serverType=server_type)
            await WebSocketService.send_message(websocket, start_message)

            # Simulate a task with 3 iterations
            await TaskService._run_task_iterations(websocket, server_type, cusno_list)

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
    async def _run_task_iterations(websocket: WebSocket, server_type: int, cusno_list: List) -> None:
        """Run task iterations with logs sent to client."""
        for i in range(3):
            await asyncio.sleep(1)
            logger.info(f"Task iteration for server_type {server_type}: {i + 1}")

            log_message = TaskLogMessage(serverType=server_type, value=i + 1)
            await WebSocketService.send_message(websocket, log_message)

    @staticmethod
    async def _run_task(websocket: WebSocket, server_type: int, cusno_list: List) -> None:
        joined_cusno_list = cusno_list.join(",")
        try:
            ssh = SSHService.connect_ssh(server_type)
            output = SSHService.execute_shell(server_type, joined_cusno_list, ssh)
            logger.info(output)
        except Exception as e:
            logger.error(e)
            raise e

    @staticmethod
    async def _reset_task_state() -> None:
        """Reset task state to available."""
        async with task_state_manager.lock:
            await task_state_manager.update_state(True)
            await task_state_manager.set_task_owner(None)


class SSHService:
    @staticmethod
    async def _tstc(command, shell, clear=1):
        asyncio.sleep(1)

        if command:
            shell.send(command + '\n')
            asyncio.sleep(1)

        if clear:
            _ = shell.recv(4096)

    @staticmethod
    async def execute_wdexgm1p(command, ssh):
        shell = ssh.invoke_shell()
        SSHService._tstc('', shell)
        SSHService._tstc('wd', shell)
        _ = shell.recv(4096)
        SSHService._tstc('2', shell)
        SSHService._tstc(command, shell, 0)

        output = ''
        while True:
            if shell.recv_ready():
                data = shell.recv(10000).decode()
                logger.info(f'{data.strip()}')
                output += data

                if "[SUCC] PostgreSQL load data unload Process" in data:
                    break
            else:
                asyncio.sleep(0.1)

        shell.close()

        return output

    async def execute_edwap1t(command, ssh):
        shell = ssh.invoke_shell()
        SSHService._tstc('', shell)
        SSHService._tstc('2', shell)
        SSHService._tstc(command, shell, 0)

        output = ''
        while True:
            if shell.recv_ready():
                data = shell.recv(100000).decode()
                logger.info(f'{data.strip()}')
                output += data

                if "[SUCC] PostgreSQL load data transfer Process" in data:
                    break
            else:
                asyncio.sleep(0.1)

        shell.close()

        return output

    async def execute_mypap1d(command, ssh):
        ssh.invoke_shell()
        stdin, stdout, stderr = ssh.exec_command(command)
        stdoutRead = stdout.read()

        output = stdoutRead.decode('utf-8')

        reg_pattern_1 = r"(update|insert) queries : \d{1,2}.\d% \(\d+\/\d+\)"
        reg_pattern_2 = r"making queries : \d{1,2}.\d %"
        cleaned_output = re.sub(reg_pattern_1, "", output)
        cleaned_output = re.sub(reg_pattern_2, "", cleaned_output)
        cleaned_output = cleaned_output.replace('\r ', '')
        logger.info(f"{cleaned_output}")

        return cleaned_output

    @staticmethod
    async def connect_ssh(server_type):
        """
        SSH 연결 함수
        - parameter : 서버 이름
        - return    : ssh 객체
        """
        try:
            if server_type == 1:
                server_name = 'wdexgm1p'
                server_host = '172.19.4.83'
            elif server_type == 2:
                server_name = 'edwap1t'
                server_host = '172.23.254.54'
            elif server_type == 3:
                server_name = 'mypap1d'
                server_host = '172.23.248.115'
            else:
                raise Exception(f"잘못된 server_type: {server_type}")

            logger.info('SSH 연결 시작')
            logger.info(f"server_name: {server_name}, \
                        hostname: {server_host},\
                        username={settings.HIWARE_ID},\
                        password={settings.HIWARE_PW}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(server_host, username=settings.HIWARE_ID, password=settings.HIWARE_PW)

            if ssh.get_transport().is_active():
                logger.info("SSH 연결 성공")
            else:
                logger.error("SSH 연결 실패")
                logger.info("SSH 연결 종료")
                ssh.close()

            return ssh

        except Exception as e:
            logger.error(f"SSH 연결 중 에러 발생 >>> {e}")
            logger.info("SSH 연결 종료")
            ssh.close()

            raise Exception(f"SSH 연결 중 에러 발생 >>> {e}")

    async def execute_shell(server_name, cusno, ssh):
        """
        대응답 Shell 실행 함수
        - parameter : 서버이름, 고객번호, ssh 객체
        - return    : 실행결과(스크립트 로그)
        """
        try:
            shells = {
                'wdexgm1p': 'vmyp_postgresql_dat_ddts.sh ',
                'edwap1t': 'vmyp_postgresql_dat_transfer.sh',
                'mypap1d': 'sh bmyp_postgresql_dat_odst.sh'
            }
            command = shells[server_name]
            if server_name == 'mdwap1p' or server_name == 'wdexgm1p':
                command += str(cusno)

            logger.info(f'대응답 SHELL 실행 시작 >>> [{command}]')
            if server_name == 'wdexgm1p':
                output = SSHService.execute_wdexgm1p(command, ssh)

            elif server_name == 'edwap1t':
                output = SSHService.execute_edwap1t(command, ssh)

            elif server_name == 'mypap1d':
                output = SSHService.execute_mypap1d(command, ssh)

            logger.info('대응답 SHELL 실행 완료')
            logger.info("SSH 연결 종료")
            ssh.close()

            return output

        except Exception as e:
            logger.error(f"대응답 SHELL 실행 중 에러 발생 >>> {e}")
            logger.info('SSH 연결 종료')
            ssh.close()

            raise Exception(f"대응답 SHELL 실행 중 에러 발생 >>> {e}")
