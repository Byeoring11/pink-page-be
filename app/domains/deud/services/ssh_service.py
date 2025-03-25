import asyncio
from fastapi import WebSocket
from app.infrastructures.websocket.services.websocket_service import WebSocketService
from app.infrastructures.ssh import SSHClientImpl, SSHConnectionConfig, SSHConnectionError, SSHCommandError
from app.domains.deud.schemas.websocket_task_schema import TaskLogMessage
from app.core.logger import logger
from app.core.config import settings


class DeudSSHService:
    def __init__(self, websocket_service: WebSocketService):
        self._websocket_service = websocket_service
        self._ssh = SSHClientImpl()

    async def execute_shell_controller(self, websocket: WebSocket, server_type: int, cusno_list: list):
        logger.info(f"Starting Deud SSH service for server_type: {server_type}")

        ssh_connection_config = SSHConnectionConfig(
            host=settings.SERVERS[server_type],
            username=settings.HIWARE_ID,
            password=settings.HIWARE_PW
        )

        try:
            await self._ssh.connect(ssh_connection_config)

            if server_type == 1:
                await self._execute_wdexgm1p(websocket, server_type, cusno_list)
            elif server_type == 2:
                await self._execute_edwap1t(websocket, server_type, cusno_list)
            elif server_type == 3:
                await self._execute_mypap1d(websocket, server_type, cusno_list)
        except SSHConnectionError as e:
            print(f"SSH 연결 실패: {e}")
        finally:
            await self._ssh.disconnect()

    async def _execute_wdexgm1p(self, websocket: WebSocket, server_type: int, cusno_list: list):
        try:
            shell = await self._ssh.create_shell()

            await shell.send_command('wd')
            _, _ = await shell.expect('choice please :')

            await shell.send_command('2')
            await asyncio.sleep(1)

            command = f"vmyp_postgresql_dat_ddts.sh {','.join(cusno_list)}"
            await shell.send_command(command)

            complete_output = ""
            is_command_completed = False
            start_time = asyncio.get_event_loop().time()
            async for chunk in shell.read_stream():
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - start_time

                log_message = TaskLogMessage(
                    serverType=server_type,
                    value={
                        "message": chunk
                    }
                )

                await self._websocket_service.send_message(websocket, log_message)

                complete_output += chunk
                if "[SUCC] PostgreSQL load data unload Process" in chunk:
                    logger.info(f"wdexgm1p Shell 실행 완료 (경과 시간: {elapsed:.2f}초)")
                    is_command_completed = True
                    break

            if not is_command_completed:
                raise SSHCommandError("커맨드 정상 종료 실패")

        except SSHCommandError as e:
            logger.error("wdexgm1p Shell 실행 실패")
            raise e

        except Exception as e:
            logger.error(f"wdexgm1p Shell 실행 중 오류 발생: {str(e)}")
            raise SSHCommandError(cause=e)

        finally:
            await shell.close_shell()

    async def _execute_edwap1t(self, websocket: WebSocket, server_type: int, cusno_list: list):
        try:
            shell = await self._ssh.create_shell()

            await shell.send_command('2')
            await asyncio.sleep(1)

            command = "vmyp_postgresql_dat_transfer.sh"
            await shell.send_command(command)

            complete_output = ""
            is_command_completed = False
            start_time = asyncio.get_event_loop().time()
            async for chunk in shell.read_stream():
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - start_time

                log_message = TaskLogMessage(
                    serverType=server_type,
                    value={
                        "message": chunk
                    }
                )

                await self._websocket_service.send_message(websocket, log_message)

                complete_output += chunk
                if "[SUCC] PostgreSQL load data transfer Process" in chunk:
                    logger.info(f"edwap1t Shell 실행 완료 (경과 시간: {elapsed:.2f}초)")
                    is_command_completed = True
                    break

            if not is_command_completed:
                raise SSHCommandError("커맨드 정상 종료 실패")

        except SSHCommandError as e:
            logger.error("edwap1t Shell 실행 실패")
            raise e

        except Exception as e:
            logger.error(f"edwap1t Shell 실행 중 오류 발생: {str(e)}")
            raise SSHCommandError(cause=e)

        finally:
            await shell.close_shell()

    async def _execute_mypap1d(self, websocket: WebSocket, server_type: int, cusno_list: list):
        try:
            shell = await self._ssh.create_shell()

            command = "sh bmyp_postgresql_dat_odst.sh"
            await shell.send_command(command)

            complete_output = ""
            is_command_completed = False
            start_time = asyncio.get_event_loop().time()
            async for chunk in shell.read_stream():
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - start_time

                log_message = TaskLogMessage(
                    serverType=server_type,
                    value={
                        "message": chunk
                    }
                )

                await self._websocket_service.send_message(websocket, log_message)

                complete_output += chunk
                if "" in chunk:
                    logger.info(f"mypap1d Shell 실행 완료 (경과 시간: {elapsed:.2f}초)")
                    is_command_completed = True
                    break

            if not is_command_completed:
                raise SSHCommandError("커맨드 정상 종료 실패")

        except SSHCommandError as e:
            logger.error("mypap1d Shell 실행 실패")
            raise e

        except Exception as e:
            logger.error(f"mypap1d Shell 실행 중 오류 발생: {str(e)}")
            raise SSHCommandError(cause=e)

        finally:
            await shell.close_shell()
