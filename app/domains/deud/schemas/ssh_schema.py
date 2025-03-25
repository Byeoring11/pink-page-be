from typing import List
from pydantic import BaseModel


class SSHServerConfig(BaseModel):
    """SSH 서버 설정"""
    setup_commands: List[str]
    main_command_template: str
    success_message: str
