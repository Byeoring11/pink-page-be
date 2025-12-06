"""BMX5 Domain SSH Service

Provides file transfer and script execution functionality for the BMX5 domain.
Demonstrates how to extend BaseSSHService for SFTP operations.
"""

from typing import Optional, List
import os
from pathlib import Path

from app.infrastructures.ssh import BaseSSHService, get_ssh_config
from app.core.logger import logger
from app.core.exceptions import SSHCommandException, Bmx5OperationFailedException


class Bmx5SSHService(BaseSSHService):
    """
    BMX5-specific SSH service with SFTP support.

    Extends BaseSSHService to provide:
    - SFTP file upload/download
    - Script file transfer and execution
    - Remote file management
    """

    def __init__(self):
        """Initialize BMX5 SSH service"""
        super().__init__()
        self.sftp_client = None

    async def connect_to_server(self, server_name: str) -> bool:
        """
        Connect to a configured server by name.

        Args:
            server_name: Server name (e.g., "mdwap1p", "mypap1d")

        Returns:
            True if connection successful
        """
        config = get_ssh_config(server_name)
        return await self.connect(
            host=config.host,
            username=config.username,
            password=config.password,
            port=config.port
        )

    async def open_sftp(self):
        """
        Open SFTP session.

        Must be called after connect() and before file operations.

        Raises:
            Bmx5OperationFailedException: If not connected or SFTP open fails
        """
        if not self.is_connected or not self.ssh_client:
            raise Bmx5OperationFailedException(
                operation="sftp_open",
                detail="Not connected to SSH server"
            )

        try:
            self.sftp_client = self.ssh_client.open_sftp()
            logger.info("[BMX5-SSH] SFTP session opened")
        except Exception as e:
            logger.error(f"[BMX5-SSH] Failed to open SFTP: {e}")
            raise Bmx5OperationFailedException(
                operation="sftp_open",
                detail=f"Failed to open SFTP session: {str(e)}"
            )

    async def close_sftp(self):
        """Close SFTP session"""
        if self.sftp_client:
            try:
                self.sftp_client.close()
                logger.info("[BMX5-SSH] SFTP session closed")
            except Exception as e:
                logger.error(f"[BMX5-SSH] Error closing SFTP: {e}")
            finally:
                self.sftp_client = None

    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        create_dirs: bool = True
    ) -> bool:
        """
        Upload file to remote server via SFTP.

        Args:
            local_path: Local file path
            remote_path: Remote file path
            create_dirs: Create remote directories if they don't exist

        Returns:
            True if upload successful

        Raises:
            Bmx5OperationFailedException: If upload fails
        """
        if not self.sftp_client:
            raise Bmx5OperationFailedException(
                operation="file_upload",
                detail="SFTP session not opened. Call open_sftp() first."
            )

        try:
            # Check local file exists
            if not os.path.exists(local_path):
                raise Bmx5OperationFailedException(
                    operation="file_upload",
                    detail=f"Local file not found: {local_path}"
                )

            # Create remote directories if needed
            if create_dirs:
                remote_dir = os.path.dirname(remote_path)
                if remote_dir:
                    await self._create_remote_dir(remote_dir)

            # Upload file
            logger.info(f"[BMX5-SSH] Uploading {local_path} -> {remote_path}")
            self.sftp_client.put(local_path, remote_path)
            logger.info(f"[BMX5-SSH] Upload completed: {remote_path}")

            return True

        except Exception as e:
            logger.error(f"[BMX5-SSH] Upload failed: {e}")
            raise Bmx5OperationFailedException(
                operation="file_upload",
                detail=f"File upload failed: {str(e)}"
            )

    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download file from remote server via SFTP.

        Args:
            remote_path: Remote file path
            local_path: Local file path

        Returns:
            True if download successful

        Raises:
            Bmx5OperationFailedException: If download fails
        """
        if not self.sftp_client:
            raise Bmx5OperationFailedException(
                operation="file_download",
                detail="SFTP session not opened. Call open_sftp() first."
            )

        try:
            # Create local directories if needed
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)

            # Download file
            logger.info(f"[BMX5-SSH] Downloading {remote_path} -> {local_path}")
            self.sftp_client.get(remote_path, local_path)
            logger.info(f"[BMX5-SSH] Download completed: {local_path}")

            return True

        except Exception as e:
            logger.error(f"[BMX5-SSH] Download failed: {e}")
            raise Bmx5OperationFailedException(
                operation="file_download",
                detail=f"File download failed: {str(e)}"
            )

    async def upload_and_execute_script(
        self,
        local_script_path: str,
        remote_script_path: Optional[str] = None,
        script_args: Optional[List[str]] = None,
        cleanup: bool = True
    ) -> tuple[str, str, int]:
        """
        Upload a script and execute it on remote server.

        Args:
            local_script_path: Local script file path
            remote_script_path: Remote path (defaults to /tmp/<filename>)
            script_args: Arguments to pass to script
            cleanup: Delete script file after execution

        Returns:
            Tuple of (stdout, stderr, exit_code)

        Raises:
            Bmx5OperationFailedException: If operation fails
        """
        # Default remote path
        if not remote_script_path:
            filename = os.path.basename(local_script_path)
            remote_script_path = f"/tmp/{filename}"

        try:
            # Ensure SFTP is open
            if not self.sftp_client:
                await self.open_sftp()

            # Upload script
            await self.upload_file(local_script_path, remote_script_path)

            # Make script executable
            logger.info(f"[BMX5-SSH] Making script executable: {remote_script_path}")
            await self.execute_command(f"chmod +x {remote_script_path}")

            # Build command
            command = remote_script_path
            if script_args:
                args_str = " ".join(str(arg) for arg in script_args)
                command = f"{command} {args_str}"

            # Execute script
            logger.info(f"[BMX5-SSH] Executing script: {command}")
            stdout, stderr, exit_code = await self.execute_command(command)

            # Cleanup
            if cleanup:
                logger.info(f"[BMX5-SSH] Cleaning up script: {remote_script_path}")
                await self.execute_command(f"rm -f {remote_script_path}")

            return stdout, stderr, exit_code

        except Exception as e:
            logger.error(f"[BMX5-SSH] Script execution failed: {e}")
            raise Bmx5OperationFailedException(
                operation="script_execution",
                detail=f"Script execution failed: {str(e)}"
            )

    async def _create_remote_dir(self, remote_dir: str):
        """Create remote directory (recursive)"""
        try:
            # Try to create directory
            self.sftp_client.mkdir(remote_dir)
        except IOError:
            # Directory might exist or parent doesn't exist
            # Try to create parent first
            parent = os.path.dirname(remote_dir)
            if parent and parent != remote_dir:
                await self._create_remote_dir(parent)
                try:
                    self.sftp_client.mkdir(remote_dir)
                except IOError:
                    pass  # Directory might already exist

    async def list_remote_files(self, remote_path: str) -> List[str]:
        """
        List files in remote directory.

        Args:
            remote_path: Remote directory path

        Returns:
            List of file names

        Raises:
            Bmx5OperationFailedException: If operation fails
        """
        if not self.sftp_client:
            raise Bmx5OperationFailedException(
                operation="list_files",
                detail="SFTP session not opened. Call open_sftp() first."
            )

        try:
            files = self.sftp_client.listdir(remote_path)
            logger.info(f"[BMX5-SSH] Listed {len(files)} files in {remote_path}")
            return files
        except Exception as e:
            logger.error(f"[BMX5-SSH] Failed to list files: {e}")
            raise Bmx5OperationFailedException(
                operation="list_files",
                detail=f"Failed to list files: {str(e)}"
            )

    async def disconnect(self):
        """Disconnect SSH and SFTP"""
        await self.close_sftp()
        await super().disconnect()
