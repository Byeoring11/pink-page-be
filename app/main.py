from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.middleware import Middleware

from core.middlewares.sqlalchemy import SQLAlchemyMiddleware
from domain import router
from core.swagger.router import router as swagger_router


def init_routers(app_: FastAPI) -> None:
    app_.include_router(swagger_router, prefix="/swagger", tags=["Swagger"])
    app_.include_router(router)


def init_listeners(app_: FastAPI) -> None:
    pass
    # @app_.exception_handler(APIException)
    # async def custom_exception_handler(request: Request, exc: APIException):
    #     return JSONResponse(
    #         status_code=exc.status_code,
    #         content=dict(
    #             status=exc.status_code,
    #             msg=exc.msg,
    #             msg_code=exc.msg_code,
    #             detail=exc.detail,
    #             code=exc.code
    #         ),
    #     )


def make_middleware() -> List[Middleware]:
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
    app_ = FastAPI(
        title="Pink-page API",
        description="This is a pink page API server made with FastAPI",
        version="0.0.1",
        docs_url=None,
        middleware=make_middleware(),
    )
    init_routers(app_)
    init_listeners(app_)

    # ROOT routing: Swagger로 redirect
    @app_.get('/')
    async def index():
        return RedirectResponse('/swagger/docs')

    return app_


app = create_app()
