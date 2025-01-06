from typing import Any
from pydantic import BaseModel


class DeudRequset(BaseModel):
    server_name: str
    user_id: str


class DeudResponse(BaseModel):
    exec_log: Any = "Hi"
