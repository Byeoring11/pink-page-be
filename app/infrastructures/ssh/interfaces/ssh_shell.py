from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator


class SSHShellInterface(ABC):
    """SSH Interactive Shell Interface"""

    @abstractmethod
    async def start_shell(self, pty_params: Optional[dict] = None) -> None:
        """Start an interactive shell session"""
        pass

    @abstractmethod
    async def send_command(self, command: str) -> None:
        """Send a command to the interactive shell"""
        pass

    @abstractmethod
    async def read_output(self, timeout: Optional[float] = None) -> str:
        """Read output from the interactive shell"""
        pass

    @abstractmethod
    async def read_stream(self) -> AsyncIterator[str]:
        """Stream output from the interactive shell"""
        pass

    @abstractmethod
    async def expect(self, pattern: str, timeout: Optional[float] = None) -> tuple[bool, str]:
        """Wait for a pattern in the output and return matched content"""
        pass

    @abstractmethod
    async def close_shell(self) -> None:
        """Close the interactive shell session"""
        pass
