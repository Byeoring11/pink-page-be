"""SSH Infrastructure Module

Provides base SSH functionality that can be extended by domain-specific services.

Usage:
    from app.infrastructures.ssh import BaseSSHService, get_ssh_config

    class MySSHService(BaseSSHService):
        async def my_custom_command(self):
            # Use self.transport, self.channel, etc.
            pass

    # Get server config
    config = get_ssh_config("mdwap1p")
    service = MySSHService()
    await service.connect(config.host, config.username, config.password)
"""

from app.infrastructures.ssh.base import BaseSSHService
from app.infrastructures.ssh.config import (
    SSHServerConfig,
    SSHConfigManager,
    get_ssh_config,
)

__all__ = [
    "BaseSSHService",
    "SSHServerConfig",
    "SSHConfigManager",
    "get_ssh_config",
]
