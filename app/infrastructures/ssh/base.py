"""기본 SSH 서비스

도메인별 SSH 서비스에서 상속받아 사용할 수 있는 공통 SSH 연결 및 인증 로직 제공
"""

import socket
import paramiko
from typing import Optional, Tuple
from abc import ABC

from app.core.logger import logger
from app.core.exceptions import (
    SSHConnectionException,
    SSHAuthException,
    SSHCommandException,
    ErrorCode,
)


class BaseSSHService(ABC):
    """
    공통 연결 및 인증 로직을 가진 기본 SSH 서비스

    도메인별 서비스는 이 클래스를 상속받아 자체 명령 실행 로직을 구현해야 함

    사용 예제:
        class StubSSHService(BaseSSHService):
            async def execute_interactive_command(self, command: str):
                # 도메인별 구현
                pass
    """

    def __init__(self):
        """SSH 서비스 초기화"""
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.transport: Optional[paramiko.Transport] = None
        self.channel: Optional[paramiko.Channel] = None
        self.is_connected: bool = False
        self._host: Optional[str] = None
        self._port: Optional[int] = None
        self._username: Optional[str] = None

    async def connect(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        timeout: float = 10.0
    ) -> bool:
        """
        인증을 포함한 SSH 서버 연결

        2단계 인증 사용:
        1. 먼저 auth_none 시도 (일부 레거시 시스템용)
        2. 비밀번호 인증으로 폴백

        Args:
            host: SSH 서버 IP
            username: SSH 사용자명
            password: SSH 비밀번호
            port: SSH 포트 (기본값: 22)
            timeout: 연결 타임아웃 (초)

        Returns:
            연결 성공 시 True, 실패 시 False

        Raises:
            SSHConnectionException: 연결 실패 시
            SSHAuthException: 인증 실패 시
        """
        self._host = host
        self._port = port
        self._username = username

        try:
            # TCP 연결
            logger.info(f"[SSH] {host}:{port}에 연결 중")
            sock = socket.create_connection((host, port), timeout=timeout)
            logger.info(f"[SSH] {host}:{port}에 TCP 연결 성공")

            # Transport 초기화
            self.transport = paramiko.Transport(sock)
            self.transport.start_client()
            logger.info(f"[SSH] {host}에 대한 SSH 핸드셰이크 완료")

            # 2단계 인증
            authenticated = await self._authenticate(username, password)

            if not authenticated:
                self.transport.close()
                raise SSHAuthException(
                    username=username,
                    detail="모든 인증 방법 실패",
                    context={"host": host, "port": port}
                )

            # 인증된 transport로 SSHClient 생성
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client._transport = self.transport

            self.is_connected = True
            logger.info(f"[SSH] {host}에 {username}로 성공적으로 연결됨")
            return True

        except socket.timeout as e:
            logger.error(f"[SSH] {host}:{port} 연결 타임아웃")
            raise SSHConnectionException(
                host=host,
                port=port,
                error_code=ErrorCode.SSH_CONNECTION_TIMEOUT,
                detail=f"{timeout}초 후 연결 타임아웃",
                original_exception=e
            )

        except socket.error as e:
            logger.error(f"[SSH] {host}:{port} 연결 중 소켓 에러: {e}")
            raise SSHConnectionException(
                host=host,
                port=port,
                error_code=ErrorCode.SSH_CONNECTION_REFUSED,
                detail=str(e),
                original_exception=e
            )

        except SSHAuthException:
            raise  # 인증 예외는 재발생

        except Exception as e:
            logger.error(f"[SSH] {host}:{port} 연결 중 예상치 못한 에러: {e}")
            raise SSHConnectionException(
                host=host,
                port=port,
                detail=f"예상치 못한 연결 에러: {str(e)}",
                original_exception=e
            )

    async def _authenticate(self, username: str, password: str) -> bool:
        """
        2단계 인증 수행

        Args:
            username: SSH 사용자명
            password: SSH 비밀번호

        Returns:
            인증 성공 시 True
        """
        authenticated = False

        # 1단계: auth_none 시도 (일부 레거시 시스템 지원)
        try:
            self.transport.auth_none(username)
            if self.transport.is_authenticated():
                logger.info(f"[SSH] {username} 인증 성공 (none)")
                return True
        except paramiko.AuthenticationException:
            logger.debug(f"[SSH] {username}에 대해 auth_none 사용 불가")
        except Exception as e:
            logger.warning(f"[SSH] {username}에 대한 auth_none 에러: {e}")

        # 2단계: 비밀번호 인증
        if not authenticated and password:
            try:
                self.transport.auth_password(username, password)
                if self.transport.is_authenticated():
                    logger.info(f"[SSH] {username} 인증 성공 (password)")
                    return True
            except paramiko.AuthenticationException as e:
                logger.error(f"[SSH] {username} 비밀번호 인증 실패")
                raise SSHAuthException(
                    username=username,
                    detail="비밀번호 인증 실패",
                    original_exception=e
                )
            except Exception as e:
                logger.error(f"[SSH] {username} 비밀번호 인증 에러: {e}")
                raise SSHAuthException(
                    username=username,
                    detail=f"인증 에러: {str(e)}",
                    original_exception=e
                )

        return False

    async def disconnect(self) -> None:
        """
        SSH 연결 해제 및 리소스 정리

        여러 번 호출해도 안전함
        """
        try:
            if self.channel and not self.channel.closed:
                self.channel.close()
                logger.debug("[SSH] 채널 닫힘")

            if self.transport and self.transport.is_active():
                self.transport.close()
                logger.debug("[SSH] Transport 닫힘")

            if self.ssh_client:
                self.ssh_client.close()
                logger.debug("[SSH] SSH 클라이언트 닫힘")

            self.is_connected = False
            logger.info(f"[SSH] {self._host}로부터 연결 해제됨")

        except Exception as e:
            logger.error(f"[SSH] 연결 해제 중 에러: {e}")

    async def execute_command(
        self,
        command: str,
        timeout: float = 30.0
    ) -> Tuple[str, str, int]:
        """
        단일 명령 실행 및 완료 대기

        기본 구현입니다. 도메인 서비스에서 더 구체적인 동작
        (예: 인터랙티브 셸)을 위해 오버라이드할 수 있음

        Args:
            command: 실행할 명령
            timeout: 명령 타임아웃 (초)

        Returns:
            (stdout, stderr, exit_code) 튜플

        Raises:
            SSHConnectionException: 연결되지 않은 경우
            SSHCommandException: 명령 실행 실패 시
        """
        if not self.is_connected or not self.ssh_client:
            raise SSHConnectionException(
                error_code=ErrorCode.SSH_NOT_CONNECTED,
                detail="SSH 서버에 연결되지 않음"
            )

        try:
            logger.info(f"[SSH] 명령 실행 중: {command}")

            stdin, stdout, stderr = self.ssh_client.exec_command(
                command,
                timeout=timeout
            )

            # 출력 읽기
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()

            logger.info(f"[SSH] 명령 완료, 종료 코드 {exit_code}")

            return stdout_data, stderr_data, exit_code

        except socket.timeout as e:
            logger.error(f"[SSH] 명령 타임아웃: {command}")
            raise SSHCommandException(
                command=command,
                error_code=ErrorCode.SSH_COMMAND_TIMEOUT,
                detail=f"{timeout}초 후 명령 타임아웃",
                original_exception=e
            )

        except Exception as e:
            logger.error(f"[SSH] 명령 실행 실패: {command} - {e}")
            raise SSHCommandException(
                command=command,
                detail=f"명령 실행 에러: {str(e)}",
                original_exception=e
            )

    def get_connection_info(self) -> dict:
        """
        현재 연결 정보 조회

        Returns:
            연결 정보가 담긴 딕셔너리
        """
        return {
            "host": self._host,
            "port": self._port,
            "username": self._username,
            "is_connected": self.is_connected,
            "transport_active": self.transport.is_active() if self.transport else False,
            "channel_open": not self.channel.closed if self.channel else False,
        }

    @staticmethod
    async def health_check(host: str, port: int = 22, timeout: float = 5.0) -> bool:
        """
        SSH 서버 health check (간단한 소켓 연결 테스트)

        Args:
            host: SSH 서버 호스트
            port: SSH 포트 (기본: 22)
            timeout: 연결 타임아웃 (초)

        Returns:
            서버가 응답하면 True, 그렇지 않으면 False
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"[SSH-Health] {host}:{port} health check 실패: {e}")
            return False

    def __del__(self):
        """객체 소멸 시 정리"""
        try:
            if self.is_connected:
                # 소멸자에서는 동기 방식으로 연결 해제
                if self.channel and not self.channel.closed:
                    self.channel.close()
                if self.transport and self.transport.is_active():
                    self.transport.close()
                if self.ssh_client:
                    self.ssh_client.close()
        except Exception as e:
            logger.debug(e)
            pass  # 소멸자에서는 에러 무시
