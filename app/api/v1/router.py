from fastapi import APIRouter
from .websockets.stub import router as stub_websocket
from .routers.stub import router as stub_router
from .routers.patchnote import router as patchnote_router

# API Endpoint 라우터 통합 관리
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(stub_router, tags=["Stub-WS"])
api_router.include_router(patchnote_router, tags=["PatchNote"])

# 웹소켓 라우터 통합 관리
websocket_router = APIRouter(prefix="/ws/v1")
websocket_router.include_router(stub_websocket, tags=["Stub-WS"])
