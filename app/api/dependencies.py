from fastapi import Depends

from app.infrastructures.websocket.services.websocket_service import WebSocketService
from app.domains.deud.services.task_manager import TaskManager
from app.domains.deud.services.task_coordinator import TaskCoordinator

# 서비스 인스턴스 관리
_websocket_service = None
_task_manager = None
_task_coordinator = None


def get_websocket_service() -> WebSocketService:
    """웹소켓 서비스 인스턴스 제공"""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = WebSocketService()
    return _websocket_service


def get_task_manager(
    websocket_service: WebSocketService = Depends(get_websocket_service)
) -> TaskManager:
    """작업 관리자 인스턴스 제공"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(websocket_service)
    return _task_manager


def get_task_coordinator(
    websocket_service: WebSocketService = Depends(get_websocket_service),
    task_manager: TaskManager = Depends(get_task_manager)
) -> TaskCoordinator:
    """작업 코디네이터 인스턴스 제공"""
    global _task_coordinator
    if _task_coordinator is None:
        _task_coordinator = TaskCoordinator(websocket_service, task_manager)
    return _task_coordinator
