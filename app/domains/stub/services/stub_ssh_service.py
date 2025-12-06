import asyncio
import socket
import select
import paramiko
from typing import Optional, Callable, Awaitable
from app.core.logger import logger
from app.core.config import settings


class StubSSHService:
    """Interactive SSH shell service based on paramikoTest.txt logic"""

    def __init__(self):
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.transport: Optional[paramiko.Transport] = None
        self.channel = None
        self.is_connected = False
        self.output_callback: Optional[Callable[[str], Awaitable[None]]] = None

    def set_output_callback(self, callback: Callable[[str], Awaitable[None]]):
        """Set callback function to handle real-time output"""
        self.output_callback = callback

    async def connect(self, host: str, username: str, password: str, port: int = 22) -> bool:
        """Connect to SSH server with authentication"""
        try:
            # TCP connection
            sock = socket.create_connection((host, port), timeout=10)
            logger.info("[STEP] TCP connection successful")

            # Transport initialization
            self.transport = paramiko.Transport(sock)
            self.transport.start_client()
            logger.info("[STEP] KEX completed")

            # Authentication (none -> password fallback)
            authenticated = False
            try:
                self.transport.auth_none(username)
                if self.transport.is_authenticated():
                    logger.info("[AUTH] none authentication successful")
                    authenticated = True
            except paramiko.AuthenticationException:
                logger.info("[AUTH] none authentication not available")
            except Exception as exc:
                logger.warning(f"[AUTH] none authentication error: {exc}")

            if not authenticated and password:
                try:
                    self.transport.auth_password(username, password)
                    if self.transport.is_authenticated():
                        logger.info("[AUTH] password authentication successful")
                        authenticated = True
                except paramiko.AuthenticationException:
                    logger.error("[AUTH] password authentication failed")
                except Exception as exc:
                    logger.error(f"[AUTH] password authentication error: {exc}")

            if not authenticated:
                logger.error("[FAIL] All authentication attempts failed")
                self.transport.close()
                return False

            # Reuse SSHClient with authenticated transport
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client._transport = self.transport

            self.is_connected = True
            return True

        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            return False

    async def start_interactive_shell(self, command: str, stop_phrase: str, recv_timeout: float = 0.1) -> None:
        """Start interactive shell and execute command with real-time streaming"""
        if not self.is_connected or not self.ssh_client:
            raise Exception("SSH not connected")

        try:
            # Open PTY shell
            self.channel = self.transport.open_session()
            self.channel.get_pty()
            self.channel.invoke_shell()
            logger.info("[INFO] Interactive shell opened")

            # Clear login buffer
            await asyncio.sleep(0.3)
            while self.channel.recv_ready():
                self.channel.recv(1024)

            # Send command
            self.channel.send(command + "\n")
            logger.info(f"[CMD] {command}")

            if self.output_callback:
                await self.output_callback(f"[CMD] {command}\n")

            # Real-time output streaming
            await self._stream_output(stop_phrase, recv_timeout)

        except Exception as e:
            logger.error(f"Interactive shell error: {e}")
            raise

    async def _stream_output(self, stop_phrase: str, recv_timeout: float) -> None:
        """Stream output in real-time and check for stop phrase"""
        partial_line = b""

        while True:
            # Check if channel is closed
            if self.channel.closed:
                logger.warning("[WARN] Server closed channel")
                if self.output_callback:
                    await self.output_callback("[WARN] Server closed channel\n")
                break

            # Non-blocking receive using select
            rlist, _, _ = select.select([self.channel], [], [], recv_timeout)
            if self.channel not in rlist:
                continue

            data = self.channel.recv(4096)
            if not data:  # EOF
                logger.info("[INFO] Server sent EOF")
                if self.output_callback:
                    await self.output_callback("[INFO] Server sent EOF\n")
                break

            # Send raw output to callback
            if self.output_callback:
                try:
                    decoded_data = data.decode('utf-8', errors='replace')
                    await self.output_callback(decoded_data)
                except Exception as e:
                    logger.error(f"Error in output callback: {e}")

            # Check for stop phrase line by line
            partial_line += data
            if b'\n' in partial_line:
                lines = partial_line.split(b'\n')
                partial_line = lines.pop()  # Keep incomplete last fragment

                for raw in lines:
                    # Remove ANSI escape codes and check for stop phrase
                    txt = raw.decode(errors="replace")
                    txt = txt.replace('\r', '')  # Remove Windows-style CR

                    if stop_phrase in txt:
                        logger.info(f"[INFO] Stop phrase found -> {stop_phrase}")
                        if self.output_callback:
                            await self.output_callback(f"\n[INFO] Stop phrase found -> {stop_phrase}\n")

                        # Send exit command and drain remaining output
                        self.channel.send("exit\n")
                        while self.channel.recv_ready():
                            remaining_data = self.channel.recv(4096)
                            if self.output_callback:
                                try:
                                    decoded_remaining = remaining_data.decode('utf-8', errors='replace')
                                    await self.output_callback(decoded_remaining)
                                except Exception as e:
                                    logger.error(f"Error in final output callback: {e}")

                        self.channel.close()
                        return

        self.channel.close()
        logger.info("[INFO] Interactive shell loop ended")

    async def send_input(self, text: str) -> None:
        """Send input to the interactive shell"""
        if self.channel and not self.channel.closed:
            self.channel.send(text)
            logger.info(f"[INPUT] {text.strip()}")

    async def disconnect(self) -> None:
        """Disconnect SSH connection"""
        try:
            if self.channel and not self.channel.closed:
                self.channel.close()
            if self.ssh_client:
                self.ssh_client.close()
            self.is_connected = False
            logger.info("[INFO] SSH connection closed")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def get_server_config(self, server_name: str) -> tuple[str, str, str]:
        """Get server configuration from settings"""
        server_configs = {
            "wdexgm1p": (settings.WDEXGM1P_IP, settings.HIWARE_ID, settings.HIWARE_PW),
            "edwap1t": (settings.EDWAP1T_IP, settings.HIWARE_ID, settings.HIWARE_PW),
            "mypap1d": (settings.MYPAP1D_IP, settings.HIWARE_ID, settings.HIWARE_PW),
        }

        if server_name.lower() in server_configs:
            return server_configs[server_name.lower()]
        else:
            raise ValueError(f"Unknown server: {server_name}")
