from pydantic import BaseModel


class SSHCommandResult(BaseModel):
    """SSH 커맨드 실행 결과 모델 클래스"""
    stdout: str
    stderr: str
    exit_code: int
    command: str
    execution_time: float  # in seconds

    @property
    def successful(self) -> bool:
        return self.exit_code == 0

    def __str__(self) -> str:
        """String representation of command result."""
        status = "Success" if self.successful else f"Failed (exit code: {self.exit_code})"
        return f"Command '{self.command}': {status}\nExecution time: {self.execution_time:.2f}s\nstdout: {self.stdout}"

# class ShellSession(BaseModel):
#     """인터랙티브 Shell 세션을 위한 모델"""

#     class Config:
#         arbitrary_types_allowed = True

#     channel: Any  # Paramiko channel object or similar
#     prompt_pattern: str = Field(default="[$#>]\\s*$")
#     timeout: int = 30
#     encoding: str = "utf-8"
#     buffer_size: int = 4096

#     # These will be set as properties with getter/setter methods implemented separately
#     _send_command: Optional[Callable[[str], None]] = None
#     _read_output: Optional[Callable[[Optional[str], Optional[int]], str]] = None
#     _wait_for_prompt: Optional[Callable[[Optional[int]], str]] = None
#     _close: Optional[Callable[[], None]] = None

#     # Method implementations will be provided by the concrete class that creates this model
#     def send_command(self, command: str) -> None:
#         """Send a command to the shell without waiting for response."""
#         if self._send_command:
#             return self._send_command(command)
#         raise NotImplementedError("send_command method not implemented")

#     def read_output(self, expect_pattern: Optional[str] = None, timeout: Optional[int] = None) -> str:
#         """Read output from the shell until a pattern is matched or timeout."""
#         if self._read_output:
#             return self._read_output(expect_pattern, timeout)
#         raise NotImplementedError("read_output method not implemented")

#     def wait_for_prompt(self, timeout: Optional[int] = None) -> str:
#         """Wait for the shell prompt and return all output received."""
#         if self._wait_for_prompt:
#             return self._wait_for_prompt(timeout)
#         raise NotImplementedError("wait_for_prompt method not implemented")

#     def execute(self, command: str, wait_for_prompt: bool = True,
#                timeout: Optional[int] = None) -> str:
#         """Execute a command and optionally wait for the prompt.

#         Args:
#             command: Command to execute
#             wait_for_prompt: Whether to wait for prompt after sending command
#             timeout: Custom timeout for this operation

#         Returns:
#             Output from the command
#         """
#         self.send_command(command + "\n")
#         if wait_for_prompt:
#             return self.wait_for_prompt(timeout)
#         return ""

#     def close(self) -> None:
#         """Close the shell session."""
#         if self._close:
#             return self._close()
#         raise NotImplementedError("close method not implemented")
