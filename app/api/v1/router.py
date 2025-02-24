from fastapi import APIRouter
from .endpoints import deud_ws

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(deud_ws.router, prefix='/deud', tags=["Deud-WS"])
