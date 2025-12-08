"""
Application Lifespan Management
애플리케이션 라이프사이클 관리
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리

    - Startup: 초기화 작업 수행
    - Shutdown: 정리 작업 수행
    """
    # ============ Startup ============
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

    # Stub Load History 데이터베이스 초기화
    from app.domains.stub.services.load_history_service import StubLoadHistoryService
    try:
        history_service = StubLoadHistoryService()
        await history_service.initialize()
        logger.info("Stub Load History 데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"Stub Load History 데이터베이스 초기화 실패: {e}", exc_info=True)
        # 데이터베이스 초기화 실패는 애플리케이션 시작을 중단하지 않음
        # (선택적 기능이므로)

    yield

    # ============ Shutdown ============
    logger.info("애플리케이션 종료 중...")

    # Health Check 서비스 중지
    try:
        await health_check_service.stop()
        logger.info("Health Check 서비스 중지됨")
    except Exception as e:
        logger.error(f"Health Check 서비스 중지 실패: {e}", exc_info=True)
