from fastapi import APIRouter, WebSocket, Depends
from app.services.websocket_service import WebsocketManager

router = APIRouter()


def get_websocket_manager():
    return WebsocketManager


@router.websocket("/deud")
async def websocket_endpoint(
    websocket: WebSocket,
    websocket_manager: WebsocketManager = Depends(get_websocket_manager)
):
    websocket_manager.connect(websocket)
