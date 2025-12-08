"""STUB Domain SSH Service

Provides interactive shell functionality with real-time output streaming
and SCP file transfer for the STUB domain.
"""

import asyncio
import select
import time
import shutil
from pathlib import Path
from typing import Optional, Callable, Awaitable

from app.infrastructures.ssh import BaseSSHService, get_ssh_config
from app.infrastructures.ssh.config import get_scp_config, SCPTransferConfig
from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import (
    SSHCommandException,
    SSHConnectionException,
    SSHSCPException,
    ErrorCode
)


class StubSSHService(BaseSSHService):
    """
    STUB-specific SSH service with interactive shell support.

    Extends BaseSSHService to provide:
    - PTY-based interactive shell
    - Real-time output streaming via callbacks
    - Stop phrase detection for automated command completion
    """

    def __init__(self):
        """Initialize STUB SSH service"""
        super().__init__()
        self.output_callback: Optional[Callable[[str], Awaitable[None]]] = None

    def set_output_callback(self, callback: Callable[[str], Awaitable[None]]):
        """
        실시간 출력 결과를 핸들링하는 콜백 함수 세팅
        Set callback function to handle real-time output.

        Args:
            callback: Async function that receives output strings
        """
        self.output_callback = callback

    async def connect_to_server(self, server_name: str) -> bool:
        """
        Connect to a configured server by name.

        Convenience method that loads configuration and connects.

        Args:
            server_name: Server name (e.g., "mdwap1p", "mypap1d")

        Returns:
            True if connection successful

        Raises:
            SSHException: If server not found
            SSHConnectionException: If connection fails
            SSHAuthException: If authentication fails
        """
        config = get_ssh_config(server_name)
        return await self.connect(
            host=config.host,
            username=config.username,
            password=config.password,
            port=config.port
        )

    async def start_interactive_shell(
        self,
        command: str,
        stop_phrase: str,
        recv_timeout: float = 0.1,
        throttle_interval: float = 0.1
    ) -> None:
        """
        인터랙티브 셸을 시작하고 실시간 스트리밍으로 커맨드를 실행

        1. PTY 기반 대화형 셸(인터랙티브 셸)을 연다
        2. 명령어를 전송한다
        3. 콜백을 통해 실시간으로 출력을 스트리밍한다
        4. 실행을 종료할 종료 구문을 감지한다
        5. 셸을 자동으로 종료한다

        Args:
            command: 실행할 명령어
            stop_phrase: 출력에서 감지하여 중지할 구문
            recv_timeout: non-blocking read 시 수신 시간 제한 (default: 0.1s)
            throttle_interval: 출력 전송 간격 (초 단위, default: 0.1s)
                              진행률 표시줄 같은 빈번한 업데이트를 제한하기 위함

        Raises:
            SSHConnectionException: 연결 실패 시
            SSHCommandException: 셸 명령어 실행 실패 시
        """
        if not self.is_connected or not self.transport:
            raise SSHConnectionException(
                error_code=ErrorCode.SSH_NOT_CONNECTED,
                detail="Not connected to SSH server"
            )

        try:
            # Open PTY shell
            self.channel = self.transport.open_session()
            self.channel.get_pty()
            self.channel.invoke_shell()
            logger.info("[STUB-SSH] Interactive shell opened")

            # Clear login buffer (wait for shell to initialize)
            await asyncio.sleep(0.3)
            while self.channel.recv_ready():
                self.channel.recv(1024)

            # Send command
            self.channel.send(command + "\n")
            logger.info(f"[STUB-SSH] Command sent: {command}")

            if self.output_callback:
                await self.output_callback(f"[호출한 명령어] {command}\n")

            # Real-time output streaming with throttling
            await self._stream_output(stop_phrase, recv_timeout, throttle_interval)

        except asyncio.CancelledError:
            # Task 취소 시 채널 정리 후 re-raise
            logger.info(f"[STUB-SSH] Interactive shell cancelled")
            if self.channel and not self.channel.closed:
                self.channel.close()
            raise  # CancelledError는 반드시 re-raise
        except Exception as e:
            logger.error(f"[STUB-SSH] Interactive shell error: {e}")
            raise SSHCommandException(
                command=command,
                detail=f"Interactive shell execution failed: {str(e)}",
                original_exception=e
            )

    async def _stream_output(
        self,
        stop_phrase: str,
        recv_timeout: float,
        throttle_interval: float
    ) -> None:
        """
        실시간으로 출력을 스트리밍하고 종료 구문을 체크한다

        비동기 함수와 함께 동작하는 select()를 사용하므로써 non-blocking I/O를 사용
        Throttling을 통해 진행률 표시줄 같은 빈번한 업데이트로 인한 과도한 전송을 방지

        Args:
            stop_phrase: Phrase to detect to stop streaming
            recv_timeout: Timeout for select() call
            throttle_interval: Minimum interval between output transmissions (seconds)
        """
        partial_line = b""
        output_buffer = ""  # 출력 버퍼
        last_send_time = 0.0  # 마지막 전송 시간
        current_line_buffer = ""  # 캐리지 리턴(\r)으로 업데이트되는 현재 줄 버퍼

        async def flush_buffer():
            """버퍼에 쌓인 출력을 클라이언트로 전송"""
            nonlocal output_buffer, current_line_buffer, last_send_time
            if output_buffer and self.output_callback:
                try:
                    await self.output_callback(output_buffer)
                    output_buffer = ""
                    current_line_buffer = ""
                    last_send_time = time.time()
                except Exception as e:
                    logger.error(f"[STUB-SSH] Error in output callback: {e}")

        while True:
            # Check if channel is closed
            if self.channel.closed:
                logger.warning("[STUB-SSH] Server closed channel")
                await flush_buffer()  # 남은 버퍼 전송
                if self.output_callback:
                    await self.output_callback("[WARN] Server closed channel\n")
                break

            # select를 이용하여 Non-blocking 수신 구현
            rlist, _, _ = select.select([self.channel], [], [], recv_timeout)
            if self.channel not in rlist:
                # 데이터가 없을 때, throttle_interval이 지났으면 버퍼 전송
                current_time = time.time()
                if output_buffer and (current_time - last_send_time) >= throttle_interval:
                    await flush_buffer()
                await asyncio.sleep(0)  # Yield to event loop
                continue

            # Receive data
            data = self.channel.recv(4096)
            if not data:  # EOF
                logger.info("[STUB-SSH] Server sent EOF")
                await flush_buffer()  # 남은 버퍼 전송
                if self.output_callback:
                    await self.output_callback("[INFO] Server sent EOF\n")
                break

            # Decode received data
            decoded_data = data.decode('utf-8', errors='replace')

            # 캐리지 리턴(\r) 처리: 진행률 표시줄 같은 경우
            if '\r' in decoded_data and '\n' not in decoded_data:
                # 같은 줄을 업데이트하는 경우 (예: 진행률 표시)
                # 이전 current_line_buffer를 새 내용으로 교체
                lines = decoded_data.split('\r')
                current_line_buffer = lines[-1]  # 마지막 업데이트만 유지
                output_buffer = current_line_buffer  # 버퍼를 현재 줄로 교체
            else:
                # 일반적인 출력 (줄바꿈 포함)
                output_buffer += decoded_data
                current_line_buffer = ""

            # Throttle: 일정 시간이 지나면 전송
            current_time = time.time()
            if (current_time - last_send_time) >= throttle_interval:
                await flush_buffer()

            # Check for stop phrase line by line
            partial_line += data
            if b'\n' in partial_line:
                lines = partial_line.split(b'\n')
                partial_line = lines.pop()  # Keep incomplete last fragment

                for raw in lines:
                    # Decode and clean line
                    txt = raw.decode(errors="replace")
                    txt = txt.replace('\r', '')  # Remove Windows-style CR

                    # Check for stop phrase
                    if stop_phrase in txt:
                        logger.info(f"[STUB-SSH] Stop phrase detected: {stop_phrase}")

                        # 버퍼에 남은 내용 즉시 전송
                        await flush_buffer()

                        if self.output_callback:
                            await self.output_callback(
                                f"\n[INFO] 셸 완료 구문 감지 확인 -> {stop_phrase}\n"
                            )

                        # Send exit command and drain remaining output
                        self.channel.send("exit\n")
                        await asyncio.sleep(0.1)  # Give time for exit to process

                        # Drain remaining output
                        remaining_buffer = ""
                        while self.channel.recv_ready():
                            remaining_data = self.channel.recv(4096)
                            remaining_buffer += remaining_data.decode('utf-8', errors='replace')

                        # 남은 출력 전송
                        if remaining_buffer and self.output_callback:
                            try:
                                await self.output_callback(remaining_buffer)
                            except Exception as e:
                                logger.error(f"[STUB-SSH] Error in final output callback: {e}")

                        self.channel.close()
                        logger.info("[STUB-SSH] Interactive shell closed (stop phrase)")
                        return

        # 루프 종료 전 남은 버퍼 전송
        await flush_buffer()

        # Close channel if not already closed
        if not self.channel.closed:
            self.channel.close()
        logger.info("[STUB-SSH] Interactive shell loop ended")

    async def send_input(self, text: str) -> None:
        """
        대화형 셸에 커맨드를 발신

        Args:
            text: Text to send to the shell

        Raises:
            SSHCommandException: If channel is closed or not available
        """
        if not self.channel or self.channel.closed:
            raise SSHCommandException(
                error_code=ErrorCode.SSH_CHANNEL_ERROR,
                detail="Channel not available or closed"
            )

        try:
            self.channel.send(text)
            logger.info(f"[STUB-SSH] Input sent: {text.strip()}")
        except Exception as e:
            logger.error(f"[STUB-SSH] Error sending input: {e}")
            raise SSHCommandException(
                detail=f"Failed to send input: {str(e)}",
                original_exception=e
            )

    async def scp_transfer(
        self,
        transfer_name: str = "stub_data_transfer",
        output_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> bool:
        """
        SCP 파일 전송 수행
        설정된 경로로 원격 서버 간 파일 전송

        개발 환경에서는 호스트 파일 시스템을 통해 직접 복사합니다.

        Args:
            transfer_name: SCP transfer configuration name (default: "stub_data_transfer")
            output_callback: 실시간 출력을 받을 콜백 함수 (선택사항)

        Returns:
            True if transfer successful, False otherwise

        Raises:
            SSHException: If configuration not found
            SSHCommandException: If SCP transfer fails
        """
        try:
            # SCP 설정 가져오기
            scp_config = get_scp_config(transfer_name)
            logger.info(f"[STUB-SCP] Starting transfer: {scp_config.description}")

            # 개발 환경: 호스트 파일 시스템을 통해 직접 복사
            if settings.ENV == "development":
                return await self._transfer_via_filesystem(scp_config, output_callback)

            # 운영 환경: SCP를 사용하여 전송
            return await self._transfer_via_scp(scp_config, output_callback)

        except SSHSCPException:
            # SSHSCPException은 그대로 re-raise
            raise
        except Exception as e:
            logger.error(f"[STUB-SCP] Error during transfer: {e}")
            raise SSHSCPException(
                transfer_name=transfer_name,
                detail=f"Unexpected error: {str(e)}",
                error_code=ErrorCode.SSH_SCP_TRANSFER_FAILED,
                original_exception=e
            )

    async def _transfer_via_filesystem(
        self,
        scp_config: SCPTransferConfig,
        output_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> bool:
        """
        개발 환경: 호스트 파일 시스템을 통해 파일 복사
        """
        try:
            # 경로 매핑 (컨테이너 경로 → 호스트 경로)
            # __file__: .../pp-backend-fastapi/app/domains/stub/services/stub_ssh_service.py
            base_dir = Path(__file__).parent.parent.parent.parent.parent  # pp-backend-fastapi/

            # 소스 경로 변환 (문자열로 처리)
            src_path_str = scp_config.src_path.replace('/nbsftp/', 'test-data/mdwap1p/nbsftp/')

            # 대상 경로 변환 (문자열로 처리)
            dst_path_str = scp_config.dst_path.replace('/shbftp/', 'test-data/mypap1d/shbftp/')
            dst_dir = base_dir / dst_path_str

            logger.info(f"[STUB-SCP] Base directory: {base_dir}")
            logger.info(f"[STUB-SCP] Source pattern: {src_path_str}")
            logger.info(f"[STUB-SCP] Destination directory: {dst_dir}")

            if output_callback:
                await output_callback(f"[INFO] Starting file transfer...\n")
                await output_callback(f"[INFO] Source: {src_path_str}\n")
                await output_callback(f"[INFO] Destination: {dst_dir}\n")

            # 대상 디렉토리 생성
            dst_dir.mkdir(parents=True, exist_ok=True)

            # 파일 복사 (glob 패턴 사용)
            # src_path_str이 "test-data/.../postgresql_unload/*.dat" 형태
            if '*' in src_path_str:
                # 패턴에서 디렉토리와 파일 패턴 분리
                parts = src_path_str.rsplit('/', 1)
                src_dir_str = parts[0]
                file_pattern = parts[1] if len(parts) > 1 else '*'

                src_dir = base_dir / src_dir_str
                src_files = list(src_dir.glob(file_pattern))
            else:
                # 와일드카드가 없으면 단일 파일
                src_files = [base_dir / src_path_str]

            logger.info(f"[STUB-SCP] Found {len(src_files)} files to transfer")

            if not src_files:
                logger.warning(f"[STUB-SCP] No files found matching pattern")
                if output_callback:
                    await output_callback("[WARN] No files found to transfer\n")
                return False

            transferred_count = 0
            for src_file in src_files:
                if not src_file.exists():
                    logger.warning(f"[STUB-SCP] File not found: {src_file}")
                    continue

                dst_file = dst_dir / src_file.name
                shutil.copy2(src_file, dst_file)
                transferred_count += 1
                logger.info(f"[STUB-SCP] Copied: {src_file.name} ({src_file.stat().st_size} bytes)")

                if output_callback:
                    await output_callback(f"[INFO] Transferred: {src_file.name}\n")

            logger.info(f"[STUB-SCP] Transfer completed: {transferred_count} files")

            if output_callback:
                await output_callback(f"[SUCCESS] Transfer completed: {transferred_count} files\n")

            return True

        except Exception as e:
            logger.error(f"[STUB-SCP] Filesystem transfer error: {e}")
            raise SSHSCPException(
                transfer_name=scp_config.name,
                detail=f"Filesystem transfer failed: {str(e)}",
                error_code=ErrorCode.SSH_SCP_TRANSFER_FAILED,
                original_exception=e
            )

    async def _transfer_via_scp(
        self,
        scp_config: SCPTransferConfig,
        output_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> bool:
        """
        운영 환경: SCP를 사용하여 파일 전송
        """
        try:
            # 소스 및 대상 서버 설정 가져오기
            src_server_config = get_ssh_config(scp_config.src_server)
            dst_server_config = get_ssh_config(scp_config.dst_server)

            # SCP URL 생성
            src_url = scp_config.get_src_url(
                src_server_config.username,
                src_server_config.host
            )
            dst_url = scp_config.get_dst_url(
                dst_server_config.username,
                dst_server_config.host
            )

            logger.info(f"[STUB-SCP] Transfer: {src_url} → {dst_url}")

            # SCP 명령 구성
            scp_opts = [
                "-P", str(src_server_config.port),
                "-o", "StrictHostKeyChecking=no",
                "-r"  # 디렉토리 전송 지원
            ]

            # sshpass를 사용한 비밀번호 인증
            # 참고: 소스와 대상 서버의 비밀번호가 같다고 가정
            cmd = [
                "sshpass", "-p", src_server_config.password,
                "scp"
            ] + scp_opts + [src_url, dst_url]

            logger.info(f"[STUB-SCP] Executing SCP command: {' '.join(cmd)}")

            # 비동기 프로세스 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # 실시간 출력 스트리밍
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                output = line.decode('utf-8', errors='replace')
                logger.debug(f"[STUB-SCP] {output.strip()}")

                if output_callback:
                    await output_callback(output)

            # 프로세스 종료 대기
            await process.wait()

            if process.returncode == 0:
                logger.info("[STUB-SCP] Transfer completed successfully")
                return True
            else:
                logger.error(f"[STUB-SCP] Transfer failed with exit code {process.returncode}")
                raise SSHSCPException(
                    transfer_name=scp_config.name,
                    src=src_url,
                    dst=dst_url,
                    detail=f"Transfer failed with exit code {process.returncode}",
                    error_code=ErrorCode.SSH_SCP_TRANSFER_FAILED
                )

        except FileNotFoundError as e:
            logger.error("[STUB-SCP] sshpass or scp command not found")
            raise SSHSCPException(
                transfer_name=scp_config.name,
                detail="sshpass or scp command not found. Please install sshpass on the server.",
                error_code=ErrorCode.SSH_SCP_COMMAND_NOT_FOUND,
                original_exception=e
            )
        except SSHSCPException:
            # SSHSCPException은 그대로 re-raise
            raise
        except Exception as e:
            logger.error(f"[STUB-SCP] Error during transfer: {e}")
            raise SSHSCPException(
                transfer_name=scp_config.name,
                detail=f"Unexpected error: {str(e)}",
                error_code=ErrorCode.SSH_SCP_TRANSFER_FAILED,
                original_exception=e
            )
