from fastapi import APIRouter
from .endpoints import deud_ws

# API Endpoint 라우터 통합 관리
api_router = APIRouter(prefix="/api/v1")

# 웹소켓 라우터 통합 관리
websocket_router = APIRouter(prefix="/ws/v1")
websocket_router.include_router(deud_ws.router, tags=["Deud-WS"])
