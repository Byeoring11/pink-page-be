from typing import Optional
from pydantic import BaseModel


class SSHCredential(BaseModel):
    """SSH 연결에 필요한 자격 증명 정보를 담는 모델"""
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None


class SSHConnectionConfig(BaseModel):
    """SSH 연결 설정 정보를 담는 모델"""
    credential: SSHCredential
    timeout: int = 10
    keep_alive_interval: int = 60
    connection_attempts: int = 3
