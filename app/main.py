from fastapi import FastAPI

from app.core.config import settings
from app.core.lifespan import lifespan
from app.middlewares import setup_middlewares
from app.api import setup_routers
from app.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    _app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESC,
        version=settings.APP_VERSION,
        docs_url=None,
        middleware=setup_middlewares(),
        lifespan=lifespan,  # 라이프사이클 추가
    )

    # 전역 예외 핸들러 등록
    register_exception_handlers(_app)

    setup_routers(_app)
    return _app


app = create_app()
