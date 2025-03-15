from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.middleware import Middleware

from app.swagger.router import router as swagger_router
from app.api.v1.router import api_router, websocket_router
from app.core.config import settings
from app.middlewares import SQLAlchemyMiddleware


def init_routers(_app: FastAPI) -> None:
    _app.include_router(swagger_router, prefix="/swagger", tags=["Swagger"])
    _app.include_router(api_router)
    _app.include_router(websocket_router)


def set_middleware() -> List[Middleware]:
    middlewares = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],     # 허용할 오리진 목록
            allow_credentials=True,  # 쿠키, 인증 정보를 포함한 요청을 허용
            allow_methods=["*"],     # 허용할 HTTP 메서드 (GET, POST, PUT, DELETE 등)
            allow_headers=["*"],     # 허용할 HTTP 헤더
        ),
        Middleware(SQLAlchemyMiddleware)
    ]
    return middlewares


def create_app():
    _app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESC,
        version=settings.APP_VERSION,
        docs_url=None,
        middleware=set_middleware(),
    )
    init_routers(_app)

    # ROOT routing: Swagger로 redirect
    @_app.get('/')
    async def index():
        return RedirectResponse('/swagger/docs')

    return _app


app = create_app()
