from pydantic import BaseModel
from typing import Optional, Literal, Any


class WebSocketMessage(BaseModel):
    type: str


class TaskStartMessage(WebSocketMessage):
    type: Literal["task_start"] = "task_start"
    serverType: int


class TaskLogMessage(WebSocketMessage):
    type: Literal["task_log"] = "task_log"
    serverType: int
    value: Any


class TaskCompleteMessage(WebSocketMessage):
    type: Literal["task_complete"] = "task_complete"
    serverType: int


class TaskErrorMessage(WebSocketMessage):
    type: Literal["task_error"] = "task_error"
    serverType: int
    message: str


class TaskCancelledMessage(WebSocketMessage):
    type: Literal["task_cancelled"] = "task_cancelled"
    serverType: int
    message: str


class TaskStateUpdateMessage(WebSocketMessage):
    type: Literal["task_state_update"] = "task_state_update"
    state: bool


class ClientMessage(BaseModel):
    action: str
    serverType: Optional[int] = None
