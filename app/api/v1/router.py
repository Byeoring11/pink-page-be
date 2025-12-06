from fastapi import APIRouter
from .websockets import deud, stub

# API Endpoint 라우터 통합 관리
api_router = APIRouter(prefix="/api/v1")

# 웹소켓 라우터 통합 관리
websocket_router = APIRouter(prefix="/ws/v1")
websocket_router.include_router(deud.router, tags=["Deud-WS"])
websocket_router.include_router(stub.router, tags=["Stub-WS"])
