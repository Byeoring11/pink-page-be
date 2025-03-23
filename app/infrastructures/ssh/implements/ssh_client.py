import paramiko
import asyncio
import socket
import time
from typing import Optional

from app.infrastructures.ssh.interfaces.ssh_client import SSHClientInterface
from app.infrastructures.ssh.models.connection import SSHConnectionConfig
from app.infrastructures.ssh.models.ssh_result import SSHCommandResult
from app.infrastructures.ssh.exceptions.ssh_exceptions import SSHConnectionError, SSHCommandError, SSHTimeoutError
from app.infrastructures.ssh.utils.ssh_sftp_utils import run_in_executor
from app.core.logger import logger


class SSHClientImpl(SSHClientInterface):
    """SSH 클라이언트 구현체 Using Paramiko"""

    def __init__(self):
        """SSH 클라이언트 초기화"""
        self._client = paramiko.SSHClient()
        self._channel = None
        self._config = None
        self._connected = False

    async def connect(self, config: SSHConnectionConfig) -> None:
        """SSH 연결 함수

        Args:
           config: SSH 연결 세부 설정

        Raises:
           SSHConnectionError: SSH 연결 에러 발생 시
        """
        self._config = config

        connect_kwargs = {
            "hostname": config.credential.host,
            "port": config.credential.port,
            "username": config.credential.username,
            "password": config.credential.password,
            "timeout": config.timeout
        }

        for attempt in range(1, config.connection_attempts + 1):
            try:
                logger.debug(f"Connecting {config.credential.host}:{config.credential.port} {attempt}/{config.connection_attempts}")
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                await run_in_executor(self._client.connect, **connect_kwargs)

                if config.keep_alive_interval > 0:
                    transport = self._client.get_transport()
                    if transport:
                        transport.set_keepalive(config.keep_alive_interval)

                self._connected = True
                logger.info(f"SSH Connected to {config.credential.host}:{config.credential.port}")
                return

            except paramiko.AuthenticationException as e:
                raise SSHConnectionError(
                    host=config.credential.host,
                    port=config.credential.port,
                    username=config.credential.username,
                    cause=e
                )

            except (paramiko.SSHException, socket.error) as e:
                if attempt == config.connection_attempts:
                    raise SSHConnectionError(
                        host=config.credential.host,
                        port=config.credential.port,
                        username=config.credential.username,
                        cause=e,
                        details={"attempt": attempt}
                    )
                logger.warning(f"Connection attempt {attempt} failed. Retrying: {str(e)}")
                await asyncio.sleep(1)

    async def disconnect(self) -> None:
        """SSH 연결 종료"""
        if self._client and self._connected:
            await run_in_executor(self._client.close)
            self._connected = False
            logger.info(f"SSH Disconnected from {self._config.credential.host}:{self._config.credential.port}")

    async def execute_command(self, command: str, timeout: Optional[int] = None) -> SSHCommandResult:
        """SSH 명령 실행"""
        if not self.is_connected():
            logger.error("SSH is not connected")
            raise SSHConnectionError("SSH is not connected")

        try:
            start_time = time.perf_counter()
            effective_timeout = timeout if timeout is not None else self._config.timeout

            logger.debug(f"Executing command: {command} with timeout: {effective_timeout}")
            stdin, stdout, stderr = await run_in_executor(self._client.exec_command, command, timeout=effective_timeout)

            stdout_data = await run_in_executor(stdout.read)
            stderr_data = await run_in_executor(stderr.read)
            exit_status = await run_in_executor(stdout.channel.recv_exit_status)

            stdout_data = stdout_data.decode('utf-8')
            stderr_data = stderr_data.decode('utf-8')

            executed_time = time.perf_counter() - start_time

            if exit_status == 0:
                logger.info(f"Command executed successfully: exit_code={exit_status}, executed_time={executed_time:.5f}s")
            else:
                logger.warning(f"Command executed successfully: exit_code={exit_status}, executed_time={executed_time:.5f}s")

            return SSHCommandResult(
                stdout=stdout_data,
                stderr=stderr_data,
                exit_code=exit_status,
                command=command,
                execution_time=executed_time
            )

        except socket.timeout as e:
            logger.error(f"Command timed out after {timeout} seconds: {str(e)}")
            raise SSHTimeoutError(
                message=f"Command timed out after {timeout} seconds",
                operation="execute_command",
                timeout=timeout,
                cause=e,
                details={"command": command}
            )

        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise SSHCommandError(
                message="Command execution failed",
                command=command,
                cause=e
            )

    def is_connected(self) -> bool:
        """연결이 활성되어 있는지 확인"""
        if not self._connected or not self._client:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()
