from abc import ABC, abstractmethod
from typing import Optional

from app.infrastructures.ssh.interfaces.ssh_shell import SSHShellInterface
from app.infrastructures.ssh.models.connection import SSHConnectionConfig
from app.infrastructures.ssh.models.ssh_result import SSHCommandResult


class SSHClientInterface(ABC):
    """SSH Client 인터페이스"""

    @abstractmethod
    async def connect(self, config: SSHConnectionConfig) -> None:
        """SSH 연결 함수

        Args:
            config: SSH 연결 세부 설정

        Raises:
            SSHConnectionError: SSH 연결 에러 발생 시
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """SSH 연결 종료 함수"""
        pass

    @abstractmethod
    async def execute_command(self, command: str, timeout: Optional[int] = None) -> SSHCommandResult:
        """원격 서버에 커맨드 실행 함수

        Args:
            command: 실행할 커맨드
            timeout: 커맨드 실행 타임아웃 시간

        Returns:
            SSHCommandResult: 커맨드 실행 결과 (stdout, stderr, exit code)

        Raises:
            SSHCommandError: 커맨드 실행 에러 발생 시
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """연결 활성 여부 체크 함수

        Returns:
            True: 연결 활성, False: 연결 비활성
        """
        pass

    @abstractmethod
    async def create_shell(self) -> SSHShellInterface:
        """인터랙티브 Shell 생성"""
        pass
