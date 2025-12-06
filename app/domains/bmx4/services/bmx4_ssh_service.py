"""BMX4 Domain SSH Service

Provides batch command execution functionality for the BMX4 domain.
Demonstrates how to extend BaseSSHService for batch operations.
"""

from typing import List, Dict, Optional, Tuple
import asyncio

from app.infrastructures.ssh import BaseSSHService, get_ssh_config
from app.core.logger import logger
from app.core.exceptions import SSHCommandException, Bmx4OperationFailedException


class Bmx4SSHService(BaseSSHService):
    """
    BMX4-specific SSH service for batch command execution.

    Extends BaseSSHService to provide:
    - Batch command execution (multiple commands in sequence)
    - Command result aggregation
    - Error handling for batch operations
    """

    def __init__(self):
        """Initialize BMX4 SSH service"""
        super().__init__()
        self.command_results: List[Dict] = []

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

    async def execute_batch_commands(
        self,
        commands: List[str],
        stop_on_error: bool = True,
        command_timeout: float = 30.0
    ) -> Dict:
        """
        Execute multiple commands in sequence.

        Args:
            commands: List of commands to execute
            stop_on_error: Stop execution if a command fails
            command_timeout: Timeout for each command

        Returns:
            Dictionary with execution results

        Raises:
            Bmx4OperationFailedException: If batch execution fails
        """
        if not self.is_connected:
            raise Bmx4OperationFailedException(
                operation="batch_execution",
                detail="Not connected to SSH server"
            )

        self.command_results = []
        failed_count = 0
        success_count = 0

        logger.info(f"[BMX4-SSH] Starting batch execution of {len(commands)} commands")

        for idx, command in enumerate(commands, 1):
            try:
                logger.info(f"[BMX4-SSH] Executing command {idx}/{len(commands)}: {command}")

                stdout, stderr, exit_code = await self.execute_command(
                    command,
                    timeout=command_timeout
                )

                result = {
                    "index": idx,
                    "command": command,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "success": exit_code == 0
                }

                self.command_results.append(result)

                if exit_code == 0:
                    success_count += 1
                    logger.info(f"[BMX4-SSH] Command {idx} completed successfully")
                else:
                    failed_count += 1
                    logger.warning(
                        f"[BMX4-SSH] Command {idx} failed with exit code {exit_code}"
                    )

                    if stop_on_error:
                        logger.warning(
                            f"[BMX4-SSH] Stopping batch execution due to error (stop_on_error=True)"
                        )
                        break

            except SSHCommandException as e:
                failed_count += 1
                logger.error(f"[BMX4-SSH] Command {idx} raised exception: {e}")

                result = {
                    "index": idx,
                    "command": command,
                    "stdout": "",
                    "stderr": str(e),
                    "exit_code": -1,
                    "success": False,
                    "error": str(e)
                }

                self.command_results.append(result)

                if stop_on_error:
                    break

        # Summary
        summary = {
            "total_commands": len(commands),
            "executed": len(self.command_results),
            "success": success_count,
            "failed": failed_count,
            "results": self.command_results
        }

        logger.info(
            f"[BMX4-SSH] Batch execution completed: "
            f"{success_count} succeeded, {failed_count} failed"
        )

        return summary

    async def execute_command_with_retry(
        self,
        command: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0
    ) -> Tuple[str, str, int]:
        """
        Execute command with retry logic.

        Args:
            command: Command to execute
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            timeout: Command timeout

        Returns:
            Tuple of (stdout, stderr, exit_code)

        Raises:
            SSHCommandException: If all retries fail
        """
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[BMX4-SSH] Executing command (attempt {attempt}/{max_retries})")

                stdout, stderr, exit_code = await self.execute_command(command, timeout)

                if exit_code == 0:
                    logger.info(f"[BMX4-SSH] Command succeeded on attempt {attempt}")
                    return stdout, stderr, exit_code
                else:
                    logger.warning(
                        f"[BMX4-SSH] Command failed on attempt {attempt} "
                        f"with exit code {exit_code}"
                    )

                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)

            except SSHCommandException as e:
                logger.warning(f"[BMX4-SSH] Command error on attempt {attempt}: {e}")
                last_exception = e

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)

        # All retries failed
        if last_exception:
            raise last_exception
        else:
            raise SSHCommandException(
                command=command,
                detail=f"Command failed after {max_retries} retries"
            )

    def get_last_results(self) -> List[Dict]:
        """
        Get results from last batch execution.

        Returns:
            List of command results
        """
        return self.command_results

    def clear_results(self):
        """Clear stored command results"""
        self.command_results = []
