from typing import List, Dict, Callable
from pydantic import BaseModel


class SSHServerCommandProfile(BaseModel):
    """SSH 서버 커맨드 프로필"""
    name: str
    setup_steps: List[Dict[str, object]]
    command_builder: Callable[[List[str]], str]
    success_indicator: str
