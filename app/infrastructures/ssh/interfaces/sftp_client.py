from abc import ABC, abstractmethod
from typing import Union, List
from pathlib import Path
from app.infrastructures.ssh.models.connection import SSHConnectionConfig
from app.infrastructures.ssh.models.file_info import FileInfo


class SFTPClientInterface(ABC):
    """SFTP 클라이언트 인터페이스"""

    @abstractmethod
    async def connect(self, config: SSHConnectionConfig) -> None:
        """제공된 설정을 사용하여 SFTP 연결을 설정합니다.

        Args:
            config: 연결 설정 정보

        Raises:
            SFTPConnectionError: 연결 실패 시 발생
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """SFTP 연결을 종료합니다."""
        pass

    @abstractmethod
    async def upload_file(self, local_path: Union[str, Path], remote_path: str) -> None:
        """로컬 파일을 원격 서버에 업로드합니다.

        Args:
            local_path: 로컬 파일 경로
            remote_path: 원격 서버의 대상 경로

        Raises:
            SFTPFileError: 파일 업로드 실패 시 발생
        """
        pass

    @abstractmethod
    async def upload_directory(
        self, local_path: Union[str, Path],
        remote_path: str,
        recursive: bool = True
    ) -> None:
        """로컬 디렉토리를 원격 서버에 업로드합니다.

        Args:
            local_path: 로컬 디렉토리 경로
            remote_path: 원격 서버의 대상 경로
            recursive: 재귀적으로 업로드할지 여부

        Raises:
            SFTPFileError: 디렉토리 업로드 실패 시 발생
        """
        pass

    @abstractmethod
    async def download_file(self, remote_path: str, local_path: Union[str, Path]) -> None:
        """원격 서버에서 파일을 다운로드합니다.

        Args:
            remote_path: 원격 서버의 파일 경로
            local_path: 로컬 대상 경로

        Raises:
            SFTPFileError: 파일 다운로드 실패 시 발생
        """
        pass

    @abstractmethod
    async def download_directory(
        self, remote_path: str,
        local_path: Union[str, Path],
        recursive: bool = True
    ) -> None:
        """원격 서버에서 디렉토리를 다운로드합니다.

        Args:
            remote_path: 원격 서버의 디렉토리 경로
            local_path: 로컬 대상 경로
            recursive: 재귀적으로 다운로드할지 여부

        Raises:
            SFTPFileError: 디렉토리 다운로드 실패 시 발생
        """
        pass

    @abstractmethod
    async def list_directory(self, remote_path: str) -> List[FileInfo]:
        """원격 디렉토리의 내용을 나열합니다.

        Args:
            remote_path: 원격 서버의 디렉토리 경로

        Returns:
            디렉토리 내용을 나타내는 FileInfo 객체 리스트

        Raises:
            SFTPFileError: 디렉토리 목록 조회 실패 시 발생
        """
        pass

    @abstractmethod
    async def file_exists(self, remote_path: str) -> bool:
        """원격 서버에 파일이 존재하는지 확인합니다.

        Args:
            remote_path: 확인할 원격 서버의 경로

        Returns:
            파일이 존재하면 True, 그렇지 않으면 False
        """
        pass

    @abstractmethod
    async def create_directory(self, remote_path: str, mode: int = 0o755) -> None:
        """원격 서버에 디렉토리를 생성합니다.

        Args:
            remote_path: 원격 서버에 생성할 경로
            mode: 디렉토리 권한

        Raises:
            SFTPFileError: 디렉토리 생성 실패 시 발생
        """
        pass

    @abstractmethod
    async def remove_file(self, remote_path: str) -> None:
        """원격 서버에서 파일을 삭제합니다.

        Args:
            remote_path: 원격 서버의 파일 경로

        Raises:
            SFTPFileError: 파일 삭제 실패 시 발생
        """
        pass

    @abstractmethod
    async def remove_directory(self, remote_path: str, recursive: bool = False) -> None:
        """원격 서버에서 디렉토리를 삭제합니다.

        Args:
            remote_path: 원격 서버의 디렉토리 경로
            recursive: 재귀적으로 삭제할지 여부

        Raises:
            SFTPFileError: 디렉토리 삭제 실패 시 발생
        """
        pass

    @abstractmethod
    async def get_file_info(self, remote_path: str) -> FileInfo:
        """원격 서버의 파일 정보를 가져옵니다.

        Args:
            remote_path: 원격 서버의 파일 경로

        Returns:
            파일 메타데이터를 포함한 FileInfo 객체

        Raises:
            SFTPFileError: 파일 정보 조회 실패 시 발생
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """연결이 활성화되어 있는지 확인합니다.

        Returns:
            연결되어 있으면 True, 그렇지 않으면 False
        """
        pass
