from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logger import logger
from app.middlewares import setup_middlewares
from app.api import setup_routers
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    logger.info("애플리케이션 시작 중...")

    # Health Check 서비스 시작
    from app.api.v1.websockets.stub import health_check_service
    try:
        await health_check_service.start()
        logger.info("Health Check 서비스 시작됨")
    except Exception as e:
        logger.error(f"Health Check 서비스 시작 실패: {e}", exc_info=True)
        # Health check 실패는 애플리케이션 시작을 중단하지 않음
        # (선택적 기능이므로)

    yield

    # Shutdown
    logger.info("애플리케이션 종료 중...")

    # Health Check 서비스 중지
    try:
        await health_check_service.stop()
        logger.info("Health Check 서비스 중지됨")
    except Exception as e:
        logger.error(f"Health Check 서비스 중지 실패: {e}", exc_info=True)


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
