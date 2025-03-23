from typing import Optional
from pydantic import BaseModel


class SSHCredential(BaseModel):
    """SSH 연결에 필요한 자격 증명 정보를 담는 모델"""
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None


class SSHConnectionConfig(SSHCredential):
    """SSH 연결 설정 정보를 담는 모델"""
    timeout: int = 10
    keep_alive_interval: int = 60
    connection_attempts: int = 3


class SSHShellTerminalConfig(BaseModel):
    """SSH Shell 터미널 설정 정보 모델"""
    term: str = 'vt100'
    width: int = 120
    height: int = 24
    width_pixels: int = 0
    height_pixels: int = 0
    environment: Optional[dict] = None


class SSHShellConnectionConfig(SSHShellTerminalConfig):
    """SSH Shell 연결 설정 정보 모델"""
    read_buffer_size: int = 4096
    default_timeout: float = 30.0
