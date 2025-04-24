from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime


class MessageType(str, Enum):
    """메시지 타입 열거형"""
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    SYSTEM = "system"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """WebSocket 메시지 기본 스키마"""
    type: MessageType = Field(..., description="메시지 유형")
    data: Any = Field(..., description="메시지 데이터")
    timestamp: datetime = Field(default_factory=datetime.now, description="메시지 생성 시간")
    sender_id: Optional[str] = Field(None, description="발신자 ID")
    target_id: Optional[str] = Field(None, description="수신자 ID (없을 경우 브로드캐스트)")


class WebSocketEvent(BaseModel):
    """WebSocket 이벤트 기본 스키마"""
    event: str = Field(..., description="이벤트 이름")
    data: Dict[str, Any] = Field(default_factory=dict, description="이벤트 데이터")
    timestamp: datetime = Field(default_factory=datetime.now, description="이벤트 생성 시간")
    sender_id: Optional[str] = Field(None, description="발신자 ID")
