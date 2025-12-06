from pydantic import BaseModel
from typing import Optional, Literal


class SSHCommandRequest(BaseModel):
    """SSH command execution request"""
    type: Literal["ssh_command"]
    server: str  # Server name (wdexgm1p, edwap1t, mypap1d)
    command: str  # Command to execute
    stop_phrase: str  # Phrase to stop execution


class SSHInputRequest(BaseModel):
    """SSH input request for interactive session"""
    type: Literal["ssh_input"]
    input: str  # Input to send to SSH session


class WebSocketResponse(BaseModel):
    """Generic WebSocket response"""
    type: str  # response type (output, error, status, complete, welcome)
    message: Optional[str] = None
    data: Optional[str] = None


class OutputResponse(WebSocketResponse):
    """SSH output response"""
    type: Literal["output"] = "output"
    data: str  # Real-time output data


class ErrorResponse(WebSocketResponse):
    """Error response"""
    type: Literal["error"] = "error"
    message: str  # Error message


class StatusResponse(WebSocketResponse):
    """Status response"""
    type: Literal["status"] = "status"
    message: str  # Status message


class CompleteResponse(WebSocketResponse):
    """Completion response"""
    type: Literal["complete"] = "complete"
    message: str  # Completion message


class WelcomeResponse(WebSocketResponse):
    """Welcome response"""
    type: Literal["welcome"] = "welcome"
    message: str  # Welcome message