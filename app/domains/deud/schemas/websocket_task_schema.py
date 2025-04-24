from enum import Enum
from typing import Literal, Any, Optional, Dict, Union
from app.infrastructures.websocket.schemas.messages import WebSocketMessage


class MessageType(str, Enum):
    """웹소켓 메시지 타입 열거형"""
    TASK_START = "task_start"
    TASK_LOG = "task_log"
    TASK_COMPLETE = "task_complete"
    TASK_ERROR = "task_error"
    TASK_CANCELLED = "task_cancelled"
    TASK_STATE_UPDATE = "task_state_update"


class ActionType(str, Enum):
    """클라이언트 요청 액션 타입 열거형"""
    START_TASK = "start_task"
    CANCEL_TASK = "task_cancel"
    GET_STATUS = "get_status"


class TaskStartMessage(WebSocketMessage):
    """작업 시작 메시지"""
    type: Literal[MessageType.TASK_START] = MessageType.TASK_START
    serverType: int


class TaskLogMessage(WebSocketMessage):
    """작업 로그 메시지"""
    type: Literal[MessageType.TASK_LOG] = MessageType.TASK_LOG
    serverType: int
    value: Union[Dict[str, Any], int, str, float]  # 더 유연한 값 타입


class TaskCompleteMessage(WebSocketMessage):
    """작업 완료 메시지"""
    type: Literal[MessageType.TASK_COMPLETE] = MessageType.TASK_COMPLETE
    serverType: int
    summary: Optional[Dict[str, Any]] = None


class TaskErrorMessage(WebSocketMessage):
    """작업 오류 메시지"""
    type: Literal[MessageType.TASK_ERROR] = MessageType.TASK_ERROR
    serverType: int
    message: str
    code: Optional[int] = None


class TaskCancelledMessage(WebSocketMessage):
    """작업 취소 메시지"""
    type: Literal[MessageType.TASK_CANCELLED] = MessageType.TASK_CANCELLED
    serverType: int
    message: str


class TaskStateUpdateMessage(WebSocketMessage):
    """작업 상태 업데이트 메시지"""
    type: Literal[MessageType.TASK_STATE_UPDATE] = MessageType.TASK_STATE_UPDATE
    state: bool
