from typing import Optional, List
from pydantic import BaseModel, Field


class WebSocketMessage(BaseModel):
    type: str


class ClientMessage(BaseModel):
    action: str
    serverType: Optional[int] = None
    cusnoList: Optional[List[str]] = Field(default_factory=list)
