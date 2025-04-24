from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.api.v1.router import api_router
from app.api.v1.router import websocket_router
from app.swagger.router import swagger_router


def setup_routers(app: FastAPI) -> None:
    app.include_router(swagger_router, prefix="/swagger", tags=["Swagger"])
    app.include_router(api_router)
    app.include_router(websocket_router)

    # ROOT routing: Swagger로 redirect
    @app.get('/')
    async def index():
        return RedirectResponse('/swagger/docs')


__all__ = [
    'setup_routers'
]
