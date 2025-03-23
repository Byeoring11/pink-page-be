import paramiko
import os
from typing import Union, Optional, List
from pathlib import Path
from datetime import datetime

from app.infrastructures.ssh.interfaces.sftp_client import SFTPClientInterface
from app.infrastructures.ssh.models.connection import SSHConnectionConfig
from app.infrastructures.ssh.models.file_info import FileInfo, FilePermission
from app.infrastructures.ssh.exceptions.sftp_exceptions import (
    SFTPConnectionError, SFTPFileError, SFTPPermissionError,
    SFTPNotFoundError, SFTPAlreadyExistsError
)
from app.infrastructures.ssh.implements.ssh_client import SSHClientImpl
from app.infrastructures.ssh.utils.ssh_sftp_utils import run_in_executor
from app.core.logger import logger


class SFTPClientImpl(SFTPClientInterface):
    """SFTP 클라이언트 구현체 Using Paramiko"""

    def __init__(self, ssh_client: Optional[SSHClientImpl] = None):
        """SFTP 클라이언트 초기화

        Args:
            ssh_client: Optional SSH client to reuse an existing connection
        """
        self._ssh_client = ssh_client
        self._is_reused_ssh_client = ssh_client is not None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._config = None
        self._connected = False

    async def connect(self, config: SSHConnectionConfig) -> None:
        """SFTP 연결 함수

        Args:
            config: SSH 연결 세부 설정

        Raises:
            SFTPConnectionError: SFTP 연결 에러 발생 시
        """
        self._config = config

        try:
            # 연결되어 있는 SSH 클라이언트가 존재한다면 재사용
            if self._ssh_client and self._ssh_client.is_connected():
                logger.debug("Reusing existing SSH connection for SFTP")
                client = self._ssh_client._client
            else:
                # 연결되어 있는 SSH 클라이언트가 없으면 새 연결
                logger.debug(f"Establishing new SSH connection to {config.credential.host}:{config.credential.port} for SFTP")
                self._ssh_client = SSHClientImpl()
                await self._ssh_client.connect(config)
                client = self._ssh_client._client

            # Open SFTP session
            self._sftp = await run_in_executor(client.open_sftp)
            self._connected = True
            logger.info(f"SFTP connection established to {config.credential.host}:{config.credential.port}")

        except Exception as e:
            raise SFTPConnectionError(
                message="Failed to establish SFTP connection",
                host=config.credential.host,
                port=config.credential.port,
                username=config.credential.username,
                cause=e
            )

    async def disconnect(self) -> None:
        """SFTP 연결 종료"""
        if self._sftp:
            await run_in_executor(self._sftp.close)
            self._sftp = None
            self._connected = False
            logger.info("SFTP connection closed")

        # If we created the SSH client, also close it
        if self._ssh_client and not self._is_reused_ssh_client:
            await self._ssh_client.disconnect()

    async def upload_file(self, local_path: Union[str, Path], remote_path: str) -> None:
        """로컬 파일을 원격 서버에 업로드합니다.

        Args:
            local_path: 로컬 파일 경로
            remote_path: 원격 서버의 대상 경로

        Raises:
            SFTPFileError: 파일 업로드 실패 시 발생
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            local_path_obj = Path(local_path).expanduser().resolve()

            if not local_path_obj.is_file():
                raise SFTPFileError(
                    message="Local path is not a file",
                    operation="upload_file",
                    path=str(local_path)
                )

            logger.debug(f"Uploading file from {local_path} to {remote_path}")
            await run_in_executor(self._sftp.put, str(local_path_obj), remote_path)
            logger.info(f"File uploaded successfully: {local_path} -> {remote_path}")

        except paramiko.SFTPError as e:
            raise SFTPPermissionError(
                message="Permission denied during file upload",
                operation="upload_file",
                path=remote_path,
                cause=e
            )

        except FileNotFoundError as e:
            raise SFTPNotFoundError(
                message="Local file not found",
                operation="upload_file",
                path=str(local_path),
                cause=e
            )

        except Exception as e:
            raise SFTPFileError(
                message="Failed to upload file",
                operation="upload_file",
                path=f"{local_path} -> {remote_path}",
                cause=e
            )

    async def upload_directory(
        self,
        local_path: Union[str, Path],
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
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            local_path_obj = Path(local_path).expanduser().resolve()
            print(local_path_obj)
            if not local_path_obj.is_dir():
                raise SFTPFileError(
                    message="Local path is not a directory",
                    operation="upload_directory",
                    path=str(local_path)
                )

            # Create remote directory if it doesn't exist
            try:
                await run_in_executor(self._sftp.stat, remote_path)
            except IOError:
                logger.debug(f"Creating remote directory: {remote_path}")
                await run_in_executor(self._sftp.mkdir, remote_path)

            # Upload all files in the directory
            for item in local_path_obj.iterdir():
                remote_item_path = os.path.join(remote_path, item.name).replace("\\", "/")

                if item.is_file():
                    await self.upload_file(item, remote_item_path)
                elif item.is_dir() and recursive:
                    await self.upload_directory(item, remote_item_path, recursive)

            logger.info(f"Directory uploaded successfully: {local_path} -> {remote_path}")

        except (SFTPConnectionError, SFTPFileError):
            # Re-raise existing SFTP exceptions
            raise

        except Exception as e:
            raise SFTPFileError(
                message="Failed to upload directory",
                operation="upload_directory",
                path=f"{local_path} -> {remote_path}",
                cause=e
            )

    async def download_file(self, remote_path: str, local_path: Union[str, Path]) -> None:
        """원격 서버에서 파일을 다운로드합니다.

        Args:
            remote_path: 원격 서버의 파일 경로
            local_path: 로컬 대상 경로

        Raises:
            SFTPFileError: 파일 다운로드 실패 시 발생
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            local_path_obj = Path(local_path).expanduser().resolve()

            # Create parent directory if it doesn't exist
            await run_in_executor(local_path_obj.parent.mkdir, parents=True, exist_ok=True)

            logger.debug(f"Downloading file from {remote_path} to {local_path}")
            await run_in_executor(self._sftp.get, remote_path, str(local_path_obj))
            logger.info(f"File downloaded successfully: {remote_path} -> {local_path}")

        except paramiko.SFTPError as e:
            raise SFTPPermissionError(
                message="Permission denied during file download",
                operation="download_file",
                path=remote_path,
                cause=e
            )

        except IOError as e:
            if "No such file" in str(e):
                raise SFTPNotFoundError(
                    message="Remote file not found",
                    operation="download_file",
                    path=remote_path,
                    cause=e
                )
            raise SFTPFileError(
                message="I/O error during file download",
                operation="download_file",
                path=remote_path,
                cause=e
            )

        except Exception as e:
            raise SFTPFileError(
                message="Failed to download file",
                operation="download_file",
                path=f"{remote_path} -> {local_path}",
                cause=e
            )

    async def download_directory(
        self,
        remote_path: str,
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
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            local_path_obj = Path(local_path).expanduser().resolve()

            # Create local directory if it doesn't exist
            await run_in_executor(local_path_obj.mkdir, parents=True, exist_ok=True)

            # List and download all items in the remote directory
            item_list: List[FileInfo] = await self.list_directory(remote_path)

            for item in item_list:
                local_item_path = local_path_obj / item.name
                remote_item_path = os.path.join(remote_path, item.name)

                if item.is_file:
                    await self.download_file(remote_item_path, local_item_path)
                elif item.is_directory and recursive:
                    await self.download_directory(remote_item_path, local_item_path, recursive)

            logger.info(f"Directory downloaded successfully: {remote_path} -> {local_path}")

        except (SFTPConnectionError, SFTPFileError):
            # Re-raise existing SFTP exceptions
            raise

        except Exception as e:
            raise SFTPFileError(
                message="Failed to download directory",
                operation="download_directory",
                path=f"{remote_path} -> {local_path}",
                cause=e
            )

    async def list_directory(self, remote_path: str) -> List[FileInfo]:
        """원격 디렉토리의 내용을 나열합니다.

        Args:
            remote_path: 원격 서버의 디렉토리 경로

        Returns:
            디렉토리 내용을 나타내는 FileInfo 객체 리스트

        Raises:
            SFTPFileError: 디렉토리 목록 조회 실패 시 발생
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            result = []
            items: List[paramiko.SFTPAttributes] = await run_in_executor(self._sftp.listdir_attr, remote_path)

            for item in items:
                item_path = os.path.join(remote_path, item.filename).replace("\\", "/")

                # Determine if it's a symlink by trying to follow it
                is_symlink = False
                symlink_target = None
                try:
                    symlink_target = await run_in_executor(self._sftp.readlink, item_path)
                    is_symlink = True
                except (IOError, paramiko.SFTPError):
                    # Not a symlink
                    pass

                # Check if directory or file (tricky with symlinks)
                is_directory = False
                is_file = False

                if is_symlink:
                    # Try to determine if symlink target is a directory
                    try:
                        # If we can listdir, it's a directory
                        await run_in_executor(self._sftp.listdir, item_path)
                        is_directory = True
                    except (IOError, paramiko.SFTPError):
                        # If we can't listdir, it might be a file or non-existent target
                        is_file = True
                else:
                    # Stat to determine file type using S_ISDIR
                    import stat
                    is_directory = stat.S_ISDIR(item.st_mode)
                    is_file = stat.S_ISREG(item.st_mode)

                # Create FileInfo object
                file_info = FileInfo(
                    path=item_path,
                    name=item.filename,
                    size=item.st_size,
                    permissions=FilePermission.from_mode(item.st_mode & 0o7777),
                    is_directory=is_directory,
                    is_file=is_file,
                    is_symlink=is_symlink,
                    uid=item.st_uid,
                    gid=item.st_gid,
                    last_modified=datetime.fromtimestamp(item.st_mtime),
                    last_accessed=datetime.fromtimestamp(item.st_atime),
                    symlink_target=symlink_target
                )

                result.append(file_info)

            return result

        except paramiko.SFTPError as e:
            raise SFTPPermissionError(
                message="Permission denied when listing directory",
                operation="list_directory",
                path=remote_path,
                cause=e
            )

        except IOError as e:
            if "No such file" in str(e):
                raise SFTPNotFoundError(
                    message="Remote directory not found",
                    operation="list_directory",
                    path=remote_path,
                    cause=e
                )
            raise SFTPFileError(
                message="I/O error when listing directory",
                operation="list_directory",
                path=remote_path,
                cause=e
            )

        except Exception as e:
            raise SFTPFileError(
                message="Failed to list directory",
                operation="list_directory",
                path=remote_path,
                cause=e
            )

    async def file_exists(self, remote_path: str) -> bool:
        """원격 서버에 파일이 존재하는지 확인합니다.

        Args:
            remote_path: 확인할 원격 서버의 경로

        Returns:
            파일이 존재하면 True, 그렇지 않으면 False
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            await run_in_executor(self._sftp.stat, remote_path)
            return True
        except IOError:
            return False

    async def create_directory(self, remote_path: str, mode: int = 0o755) -> None:
        """원격 서버에 디렉토리를 생성합니다.

        Args:
            remote_path: 원격 서버에 생성할 경로
            mode: 디렉토리 권한

        Raises:
            SFTPFileError: 디렉토리 생성 실패 시 발생
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            if await self.file_exists(remote_path):
                raise SFTPAlreadyExistsError(
                    message="Remote directory already exists",
                    operation="create_directory",
                    path=remote_path
                )

            logger.debug(f"Creating remote directory: {remote_path}")
            await run_in_executor(self._sftp.mkdir, remote_path, mode)
            logger.info(f"Directory created successfully: {remote_path}")

        except SFTPAlreadyExistsError:
            # Re-raise the existing exception
            raise

        except paramiko.SFTPError as e:
            raise SFTPPermissionError(
                message="Permission denied when creating directory",
                operation="create_directory",
                path=remote_path,
                cause=e
            )

        except Exception as e:
            raise SFTPFileError(
                message="Failed to create directory",
                operation="create_directory",
                path=remote_path,
                cause=e
            )

    async def remove_file(self, remote_path: str) -> None:
        """원격 서버에서 파일을 삭제합니다.

        Args:
            remote_path: 원격 서버의 파일 경로

        Raises:
            SFTPFileError: 파일 삭제 실패 시 발생
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            if not await self.file_exists(remote_path):
                raise SFTPNotFoundError(
                    message="Remote file not found",
                    operation="remove_file",
                    path=remote_path
                )

            # Check if it's a directory
            try:
                await run_in_executor(self._sftp.listdir, remote_path)
                raise SFTPFileError(
                    message="Remote path is a directory, not a file",
                    operation="remove_file",
                    path=remote_path
                )
            except IOError:
                # Not a directory, proceed with removal
                pass

            logger.debug(f"Removing remote file: {remote_path}")
            self._sftp.remove(remote_path)
            logger.info(f"File removed successfully: {remote_path}")

        except SFTPNotFoundError:
            # Re-raise the existing exception
            raise

        except paramiko.SFTPError as e:
            raise SFTPPermissionError(
                message="Permission denied when removing file",
                operation="remove_file",
                path=remote_path,
                cause=e
            )

        except Exception as e:
            raise SFTPFileError(
                message="Failed to remove file",
                operation="remove_file",
                path=remote_path,
                cause=e
            )

    async def remove_directory(self, remote_path: str, recursive: bool = False) -> None:
        """원격 서버에서 디렉토리를 삭제합니다.

        Args:
            remote_path: 원격 서버의 디렉토리 경로
            recursive: 재귀적으로 삭제할지 여부

        Raises:
            SFTPFileError: 디렉토리 삭제 실패 시 발생
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            if not await self.file_exists(remote_path):
                raise SFTPNotFoundError(
                    message="Remote directory not found",
                    operation="remove_directory",
                    path=remote_path
                )

            # Check if it's actually a directory
            try:
                items = await self.list_directory(remote_path)
            except IOError:
                raise SFTPFileError(
                    message="Remote path is not a directory",
                    operation="remove_directory",
                    path=remote_path
                )

            # If items exist and not recursive, raise error
            if items and not recursive:
                raise SFTPFileError(
                    message="Directory not empty and recursive removal not specified",
                    operation="remove_directory",
                    path=remote_path
                )

            # Remove contents recursively if needed
            if recursive and items:
                for item in items:
                    item_path = os.path.join(remote_path, item.name)
                    if item.is_directory:
                        await self.remove_directory(item_path, recursive=True)
                    else:
                        await self.remove_file(item_path)

            # Remove the directory itself
            logger.debug(f"Removing remote directory: {remote_path}")
            await run_in_executor(self._sftp.rmdir, remote_path)
            logger.info(f"Directory removed successfully: {remote_path}")

        except (SFTPNotFoundError, SFTPFileError):
            # Re-raise existing exceptions
            raise

        except paramiko.SFTPError as e:
            raise SFTPPermissionError(
                message="Permission denied when removing directory",
                operation="remove_directory",
                path=remote_path,
                cause=e
            )

        except Exception as e:
            raise SFTPFileError(
                message="Failed to remove directory",
                operation="remove_directory",
                path=remote_path,
                cause=e
            )

    async def get_file_info(self, remote_path: str) -> FileInfo:
        """원격 서버의 파일 정보를 가져옵니다.

        Args:
            remote_path: 원격 서버의 파일 경로

        Returns:
            파일 메타데이터를 포함한 FileInfo 객체

        Raises:
            SFTPFileError: 파일 정보 조회 실패 시 발생
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")

        try:
            stat: paramiko.SFTPAttributes = await run_in_executor(self._sftp.stat, remote_path)
            filename = os.path.basename(remote_path)

            is_symlink = False
            symlink_target = None
            try:
                symlink_target = await run_in_executor(self._sftp.readlink, remote_path)
                is_symlink = True
            except (IOError, paramiko.SFTPError):
                pass

            import stat as stat_lib
            is_directory = stat_lib.S_ISDIR(stat.st_mode)
            is_file = stat_lib.S_ISREG(stat.st_mode)

            return FileInfo(
                path=remote_path,
                name=filename,
                size=stat.st_size,
                permissions=FilePermission.from_mode(stat.st_mode & 0o7777),
                is_directory=is_directory,
                is_file=is_file,
                is_symlink=is_symlink,
                uid=stat.st_uid,
                gid=stat.st_gid,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                last_accessed=datetime.fromtimestamp(stat.st_atime),
                symlink_target=symlink_target
            )

        except IOError as e:
            if "No such file" in str(e):
                raise SFTPNotFoundError(
                    message="Remote file not found",
                    operation="get_file_info",
                    path=remote_path,
                    cause=e
                )
            raise SFTPFileError(
                message="I/O error when getting file info",
                operation="get_file_info",
                path=remote_path,
                cause=e
            )

        except Exception as e:
            raise SFTPFileError(
                message="Failed to get file info",
                operation="get_file_info",
                path=remote_path,
                cause=e
            )

    def is_connected(self) -> bool:
        """연결이 활성화되어 있는지 확인합니다.

        Returns:
            연결되어 있으면 True, 그렇지 않으면 False
        """
        return (self._connected and self._sftp is not None and self._ssh_client is not None and self._ssh_client.is_connected())
