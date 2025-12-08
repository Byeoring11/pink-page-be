"""SSH Server Configuration Management

Centralized management of SSH server configurations.
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from app.core.config import settings
from app.core.exceptions import SSHException, ErrorCode


@dataclass
class SSHServerConfig:
    """SSH server configuration"""
    name: str
    host: str
    port: int
    username: str
    password: str
    description: Optional[str] = None

    def to_tuple(self) -> Tuple[str, int, str, str]:
        """Convert to tuple (host, port, username, password)"""
        return (self.host, self.port, self.username, self.password)


@dataclass
class SCPTransferConfig:
    """SCP file transfer configuration"""
    name: str
    src_server: str  # Source server name
    src_path: str    # Source file path
    dst_server: str  # Destination server name
    dst_path: str    # Destination file path
    description: Optional[str] = None

    def get_src_url(self, username: str, host: str) -> str:
        """Get source URL for SCP command"""
        return f"{username}@{host}:{self.src_path}"

    def get_dst_url(self, username: str, host: str) -> str:
        """Get destination URL for SCP command"""
        return f"{username}@{host}:{self.dst_path}"


class SSHConfigManager:
    """
    SSH configuration manager.

    Provides centralized access to SSH server configurations
    and SCP transfer configurations.
    """

    # Server configurations loaded from environment
    _SERVERS: Dict[str, SSHServerConfig] = {}
    _SCP_TRANSFERS: Dict[str, SCPTransferConfig] = {}

    @classmethod
    def _initialize(cls):
        """Initialize server and SCP transfer configurations from settings"""
        if cls._SERVERS:
            return  # Already initialized

        # HIWARE servers (from environment variables)
        cls._SERVERS = {
            "mdwap1p": SSHServerConfig(
                name="mdwap1p",
                host=settings.MDWAP1P_IP,
                port=settings.MDWAP1P_PORT,
                username=settings.HIWARE_ID,
                password=settings.HIWARE_PW,
                description="MDWAP1P HIWARE Server"
            ),
            "mypap1d": SSHServerConfig(
                name="mypap1d",
                host=settings.MYPAP1D_IP,
                port=settings.MYPAP1D_PORT,
                username=settings.HIWARE_ID,
                password=settings.HIWARE_PW,
                description="MYPAP1D HIWARE Server"
            ),
        }

        # SCP transfer configurations
        # 개발 환경과 운영 환경 모두 동일한 경로 사용
        cls._SCP_TRANSFERS = {
            "stub_data_transfer": SCPTransferConfig(
                name="stub_data_transfer",
                src_server="mdwap1p",
                src_path="/nbsftp/myd/myp/snd/postgresql_unload/*.dat",
                dst_server="mypap1d",
                dst_path="/shbftp/myd/myp/rcv/mock/",
                description="STUB domain data transfer (mdwap1p → mypap1d)"
            ),
        }

    @classmethod
    def get_config(cls, server_name: str) -> SSHServerConfig:
        """
        Get SSH server configuration by name.

        Args:
            server_name: Server name (case-insensitive)

        Returns:
            SSHServerConfig object

        Raises:
            SSHException: If server configuration not found
        """
        cls._initialize()

        server_key = server_name.lower()
        if server_key not in cls._SERVERS:
            raise SSHException(
                error_code=ErrorCode.SSH_SERVER_NOT_FOUND,
                detail=f"Server '{server_name}' not found in configuration",
                context={
                    "server_name": server_name,
                    "available_servers": list(cls._SERVERS.keys())
                }
            )

        return cls._SERVERS[server_key]

    @classmethod
    def get_connection_params(cls, server_name: str) -> Tuple[str, int, str, str]:
        """
        Get connection parameters as tuple.

        Args:
            server_name: Server name

        Returns:
            Tuple of (host, port, username, password)

        Raises:
            SSHException: If server configuration not found
        """
        config = cls.get_config(server_name)
        return config.to_tuple()

    @classmethod
    def list_servers(cls) -> Dict[str, SSHServerConfig]:
        """
        List all available server configurations.

        Returns:
            Dictionary of server_name -> SSHServerConfig
        """
        cls._initialize()
        return cls._SERVERS.copy()

    @classmethod
    def add_server(
        cls,
        name: str,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        description: Optional[str] = None
    ):
        """
        Add a custom server configuration (runtime).

        Useful for dynamic server configuration or testing.

        Args:
            name: Server name (will be converted to lowercase)
            host: SSH host
            username: SSH username
            password: SSH password
            port: SSH port (default: 22)
            description: Optional description
        """
        cls._initialize()

        server_key = name.lower()
        cls._SERVERS[server_key] = SSHServerConfig(
            name=server_key,
            host=host,
            port=port,
            username=username,
            password=password,
            description=description
        )

    @classmethod
    def remove_server(cls, name: str) -> bool:
        """
        Remove a server configuration (runtime).

        Args:
            name: Server name

        Returns:
            True if removed, False if not found
        """
        cls._initialize()

        server_key = name.lower()
        if server_key in cls._SERVERS:
            del cls._SERVERS[server_key]
            return True
        return False

    @classmethod
    def get_scp_config(cls, transfer_name: str) -> SCPTransferConfig:
        """
        Get SCP transfer configuration by name.

        Args:
            transfer_name: Transfer configuration name

        Returns:
            SCPTransferConfig object

        Raises:
            SSHException: If transfer configuration not found
        """
        cls._initialize()

        transfer_key = transfer_name.lower()
        if transfer_key not in cls._SCP_TRANSFERS:
            raise SSHException(
                error_code=ErrorCode.SSH_CONFIG_ERROR,
                detail=f"SCP transfer '{transfer_name}' not found in configuration",
                context={
                    "transfer_name": transfer_name,
                    "available_transfers": list(cls._SCP_TRANSFERS.keys())
                }
            )

        return cls._SCP_TRANSFERS[transfer_key]

    @classmethod
    def list_scp_transfers(cls) -> Dict[str, SCPTransferConfig]:
        """
        List all available SCP transfer configurations.

        Returns:
            Dictionary of transfer_name -> SCPTransferConfig
        """
        cls._initialize()
        return cls._SCP_TRANSFERS.copy()


# Convenience functions
def get_ssh_config(server_name: str) -> SSHServerConfig:
    """
    Convenience function to get SSH config.

    Args:
        server_name: Server name

    Returns:
        SSHServerConfig object
    """
    return SSHConfigManager.get_config(server_name)


def get_scp_config(transfer_name: str) -> SCPTransferConfig:
    """
    Convenience function to get SCP transfer config.

    Args:
        transfer_name: Transfer configuration name

    Returns:
        SCPTransferConfig object
    """
    return SSHConfigManager.get_scp_config(transfer_name)
