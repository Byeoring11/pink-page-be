# app/infrastructures/ssh/implements/ssh_shell_impl.py
import asyncio
import re
import time
from typing import Optional, AsyncIterator

import paramiko
from paramiko.channel import Channel

from app.infrastructures.ssh.interfaces.ssh_shell import SSHShellInterface
from app.infrastructures.ssh.models.connection import SSHConnectionConfig, SSHShellConnectionConfig
from app.infrastructures.ssh.exceptions.ssh_exceptions import (
    SSHConnectionError, SSHCommandError, SSHTimeoutError
)
from app.infrastructures.ssh.utils.ssh_sftp_utils import run_in_executor
from app.core.logger import logger


class SSHShellImpl(SSHShellInterface):
    """SSH 인터랙티브 Shell 구현체 Using Paramiko"""

    def __init__(self, client: paramiko.SSHClient, config: SSHConnectionConfig):
        """SSH 인터랙티브 Shell 초기화

        Args:
            client: 연결된 Paramiko SSH 클라이언트
            config: SSH 연결 설정
        """
        self._client = client
        self._config = config
        self._channel: Optional[Channel] = None
        self._shell_config = SSHShellConnectionConfig()
        self._buffer = ""
        self._shell_active = False
        self._prompt = None

    async def start_shell(self, shell_config: Optional[SSHShellConnectionConfig] = None) -> None:
        """인터랙티브 Shell 세션 시작

        Args:
            shell_config: Shell 설정 (기본값 사용시 None)

        Raises:
            SSHConnectionError: SSH 연결이 없거나 채널 오픈 실패시
        """
        if not self._client or not self._client.get_transport() or not self._client.get_transport().is_active():
            raise SSHConnectionError("SSH is not connected")

        try:
            if shell_config:
                self._shell_config = shell_config

            logger.debug(f"Opening interactive shell to {self._config.credential.host}")
            self._channel = await run_in_executor(self._client.invoke_shell,
                                                  term=self._shell_config.term,
                                                  width=self._shell_config.width,
                                                  height=self._shell_config.height,
                                                  width_pixels=self._shell_config.width_pixels,
                                                  height_pixels=self._shell_config.height_pixels,
                                                  environment=self._shell_config.environment)

            # Set to non-blocking mode
            await run_in_executor(self._channel.setblocking, 0)
            self._shell_active = True

            # Initial read to clear welcome message
            await asyncio.sleep(0.5)  # Give the shell a moment to initialize
            await self._save_initial_prompt()

            logger.info(f"Interactive shell started on {self._config.credential.host}")

        except paramiko.SSHException as e:
            logger.error(f"Failed to open interactive shell: {str(e)}")
            raise SSHConnectionError(
                host=self._config.credential.host,
                port=self._config.credential.port,
                username=self._config.credential.username,
                cause=e,
                details={"operation": "start_shell"}
            )

    async def send_command(self, command: str) -> None:
        """인터랙티브 Shell에 명령어 전송

        Args:
            command: 실행할 명령어

        Raises:
            SSHConnectionError: Shell이 활성화되지 않은 경우
            SSHCommandError: 명령어 전송 실패시
        """
        if not self._shell_active or not self._channel:
            raise SSHConnectionError("Interactive shell is not active")

        try:
            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'

            logger.debug(f"Sending command to shell: {command.strip()}")
            await run_in_executor(self._channel.sendall, command)

        except Exception as e:
            logger.error(f"Failed to send command to shell: {str(e)}")
            raise SSHCommandError(
                message="Failed to send command to interactive shell",
                command=command,
                cause=e
            )

    async def read_output(self, timeout: Optional[float] = None) -> str:
        """인터랙티브 Shell의 출력 읽기

        Args:
            timeout: 출력 대기 타임아웃 (초)

        Returns:
            str: 읽어들인 출력 데이터

        Raises:
            SSHConnectionError: Shell이 활성화되지 않은 경우
            SSHTimeoutError: 타임아웃 발생시
        """
        if not self._shell_active or not self._channel:
            raise SSHConnectionError("Interactive shell is not active")

        effective_timeout = timeout if timeout is not None else self._shell_config.default_timeout
        output = ""
        start_time = time.perf_counter()

        try:
            while time.perf_counter() - start_time < effective_timeout:
                if self._channel.recv_ready():
                    chunk = await run_in_executor(self._channel.recv, self._shell_config.read_buffer_size)
                    decoded_chunk = chunk.decode('utf-8', errors='replace')
                    output += decoded_chunk

                    # If we got some data and there's no more data immediately available, return
                    if output and not self._channel.recv_ready():
                        break

                # Short pause to prevent CPU spinning
                await asyncio.sleep(0.05)

                # If the channel is closed, we're done
                if self._channel.closed:
                    self._shell_active = False
                    logger.warning("Shell channel closed unexpectedly")
                    break

            # If we didn't get any output and we've reached the timeout
            if not output and time.perf_counter() - start_time >= effective_timeout:
                logger.warning(f"Timeout waiting for shell output after {effective_timeout} seconds")
                raise SSHTimeoutError(
                    message=f"Timeout waiting for shell output after {effective_timeout} seconds",
                    operation="read_output",
                    timeout=effective_timeout
                )

            # Append output to buffer for commands like expect
            self._buffer += output
            return output

        except SSHTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error reading from shell: {str(e)}")
            raise SSHCommandError(
                message="Failed to read from interactive shell",
                command="read_output",
                cause=e
            )

    async def read_stream(self) -> AsyncIterator[str]:
        """인터랙티브 Shell의 출력을 스트림으로 읽기

        Yields:
            str: 읽어들인 출력 데이터 조각

        Raises:
            SSHConnectionError: Shell이 활성화되지 않은 경우
        """
        if not self._shell_active or not self._channel:
            raise SSHConnectionError("Interactive shell is not active")

        while self._shell_active and not self._channel.closed:
            if self._channel.recv_ready():
                chunk = await run_in_executor(self._channel.recv, self._shell_config.read_buffer_size)
                if not chunk:  # Connection closed
                    self._shell_active = False
                    break

                decoded_chunk = chunk.decode('utf-8', errors='replace')
                self._buffer += decoded_chunk
                yield decoded_chunk
            else:
                await asyncio.sleep(0.1)  # Short pause to prevent CPU spinning

    async def expect(self, pattern: str, timeout: Optional[float] = None) -> tuple[bool, str]:
        """특정 패턴이 출력에 나타날 때까지 대기

        Args:
            pattern: 대기할 정규식 패턴
            timeout: 패턴 대기 타임아웃 (초)

        Returns:
            tuple[bool, str]: (패턴 매치 여부, 읽어들인 출력)

        Raises:
            SSHConnectionError: Shell이 활성화되지 않은 경우
            SSHTimeoutError: 타임아웃 발생시
        """
        if not self._shell_active or not self._channel:
            raise SSHConnectionError("Interactive shell is not active")

        effective_timeout = timeout if timeout is not None else self._shell_config.default_timeout
        start_time = time.perf_counter()
        pattern_obj = re.compile(pattern)

        # First check if pattern is already in buffer
        match = pattern_obj.search(self._buffer)
        if match:
            result = self._buffer
            self._buffer = ""  # Clear buffer after match
            return True, result

        # Wait for pattern in incoming data
        accumulated_output = self._buffer
        self._buffer = ""  # Clear buffer as we're accumulating separately

        try:
            while time.perf_counter() - start_time < effective_timeout:
                if self._channel.recv_ready():
                    chunk = await run_in_executor(self._channel.recv, self._shell_config.read_buffer_size)
                    if not chunk:  # Connection closed
                        self._shell_active = False
                        break

                    decoded_chunk = chunk.decode('utf-8', errors='replace')
                    accumulated_output += decoded_chunk

                    # Check if pattern matches
                    match = pattern_obj.search(accumulated_output)
                    if match:
                        return True, accumulated_output

                # Short pause to prevent CPU spinning
                await asyncio.sleep(0.05)

                # If the channel is closed, we're done
                if self._channel.closed:
                    self._shell_active = False
                    logger.warning("Shell channel closed unexpectedly")
                    break

            # If we've reached the timeout without finding the pattern
            if time.perf_counter() - start_time >= effective_timeout:
                logger.warning(f"Timeout waiting for pattern '{pattern}' after {effective_timeout} seconds")
                return False, accumulated_output

            return False, accumulated_output

        except Exception as e:
            logger.error(f"Error during expect operation: {str(e)}")
            raise SSHCommandError(
                message="Failed during expect operation",
                command=f"expect '{pattern}'",
                cause=e
            )

    async def close_shell(self) -> None:
        """인터랙티브 Shell 세션 종료"""
        if self._channel and not self._channel.closed:
            try:
                # Send exit command
                await run_in_executor(self._channel.sendall, "exit\n")

                # Wait briefly for clean exit
                await asyncio.sleep(0.5)

                # Close channel
                await run_in_executor(self._channel.close)
                logger.info(f"Interactive shell closed on {self._config.credential.host}")
            except Exception as e:
                logger.warning(f"Error while closing shell: {str(e)}")
            finally:
                self._shell_active = False
                self._channel = None

    async def get_initail_prompt(self) -> str:
        return self._prompt

    async def _save_initial_prompt(self) -> None:
        prompt_pattern = r"[\r\n]([^@]+@[^:]+:[^$#>]*[$#>])\s*$"

        initial_output = await self.read_output(timeout=1.0)

        prompt_match = re.search(prompt_pattern, initial_output)
        if prompt_match:
            prompt = prompt_match.group(1)
            logger.debug(f"탐지된 프롬프트: {prompt}")
        else:
            prompt = "$"  # 기본값 설정
            logger.warning(f"프롬프트를 탐지할 수 없습니다. 기본값 사용: {prompt}")

        self._prompt = prompt
