"""SSH 서버 Health Check 서비스

백그라운드에서 주기적으로 SSH 서버 상태를 체크하고
상태 변경 시 모든 WebSocket 클라이언트에게 브로드캐스트
"""

import asyncio
from typing import Dict, Optional, Callable, Awaitable
from datetime import datetime

from app.core.logger import logger
from app.infrastructures.ssh import BaseSSHService
from app.infrastructures.ssh.config import SSHConfigManager
from app.core.exceptions import (
    SSHHealthCheckServiceException,
    SSHHealthCheckException,
    ErrorCode,
)


class ServerHealthStatus:
    """서버 health 상태"""

    def __init__(self, server_name: str, host: str, port: int = 22):
        self.server_name = server_name
        self.host = host
        self.port = port
        self.is_healthy = False
        self.last_checked: Optional[datetime] = None
        self.consecutive_failures = 0
        self.consecutive_successes = 0

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "server_name": self.server_name,
            "host": self.host,
            "port": self.port,
            "is_healthy": self.is_healthy,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
        }


class HealthCheckService:
    """
    SSH 서버 health check를 백그라운드에서 주기적으로 수행하는 서비스

    특징:
    - 주기적 health check 수행
    - 상태 변경 감지 및 콜백 호출
    - 여러 서버 동시 모니터링
    """

    def __init__(
        self,
        check_interval: float = 30.0,  # 30초마다 체크
        timeout: float = 5.0,  # health check 타임아웃
    ):
        """
        Health check 서비스 초기화

        Args:
            check_interval: health check 간격 (초)
            timeout: health check 타임아웃 (초)
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.server_statuses: Dict[str, ServerHealthStatus] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._on_status_change: Optional[Callable[[str, bool, ServerHealthStatus], Awaitable[None]]] = None

    def set_status_change_callback(
        self,
        callback: Callable[[str, bool, ServerHealthStatus], Awaitable[None]]
    ):
        """
        상태 변경 콜백 설정

        Args:
            callback: (server_name, is_healthy, status) -> None 콜백 함수
        """
        self._on_status_change = callback

    def add_server(self, server_name: str, host: str, port: int = 22):
        """
        모니터링할 서버 추가

        Args:
            server_name: 서버 이름
            host: 호스트
            port: 포트
        """
        if server_name not in self.server_statuses:
            self.server_statuses[server_name] = ServerHealthStatus(server_name, host, port)
            logger.info(f"[HealthCheck] 서버 추가: {server_name} ({host}:{port})")

    async def start(self):
        """백그라운드 health check 시작"""
        if self._running:
            logger.warning("[HealthCheck] Health check가 이미 실행 중입니다")
            raise SSHHealthCheckServiceException(
                detail="Health check service is already running",
                error_code=ErrorCode.SSH_HEALTH_CHECK_SERVICE_ALREADY_RUNNING
            )

        try:
            # 설정된 모든 서버 자동 추가
            ssh_servers = SSHConfigManager.list_servers()
            for server_name, config in ssh_servers.items():
                self.add_server(server_name, config.host, config.port)

            self._running = True
            self._task = asyncio.create_task(self._health_check_loop())
            logger.info(f"[HealthCheck] Health check 시작 (간격: {self.check_interval}초)")
        except SSHHealthCheckServiceException:
            # 이미 발생한 health check 예외는 재발생
            raise
        except Exception as e:
            self._running = False
            logger.error(f"[HealthCheck] Health check 시작 실패: {e}")
            raise SSHHealthCheckServiceException(
                detail=f"Failed to start health check service: {str(e)}",
                error_code=ErrorCode.SSH_HEALTH_CHECK_SERVICE_START_FAILED,
                original_exception=e
            )

    async def stop(self):
        """백그라운드 health check 중지"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[HealthCheck] Health check 중지됨")

    async def _health_check_loop(self):
        """Health check 루프"""
        while self._running:
            try:
                # 모든 서버 체크
                await self._check_all_servers()

                # 다음 체크까지 대기
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info("[HealthCheck] Health check 루프 취소됨")
                break
            except Exception as e:
                logger.error(f"[HealthCheck] Health check 루프 에러: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_all_servers(self):
        """모든 서버 health check 수행"""
        tasks = []
        for server_name, status in self.server_statuses.items():
            tasks.append(self._check_server(server_name, status))

        # 모든 서버를 병렬로 체크
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_server(self, server_name: str, status: ServerHealthStatus):
        """단일 서버 health check"""
        try:
            # Health check 수행
            is_healthy = await BaseSSHService.health_check(
                status.host,
                status.port,
                self.timeout
            )

            # 이전 상태 저장
            was_healthy = status.is_healthy

            # 상태 업데이트
            status.last_checked = datetime.now()

            if is_healthy:
                status.consecutive_successes += 1
                status.consecutive_failures = 0

                # 첫 성공 또는 복구된 경우
                if not was_healthy and status.consecutive_successes >= 1:
                    status.is_healthy = True
                    logger.info(f"[HealthCheck] {server_name} 복구됨")

                    # 상태 변경 콜백 호출
                    if self._on_status_change:
                        try:
                            await self._on_status_change(server_name, True, status)
                        except Exception as callback_error:
                            logger.error(
                                f"[HealthCheck] {server_name} 상태 변경 콜백 실행 실패: {callback_error}",
                                exc_info=True
                            )
                            # 콜백 실패는 health check 자체를 중단하지 않음
                elif was_healthy:
                    # 계속 건강한 상태
                    logger.debug(f"[HealthCheck] {server_name} 정상")
                else:
                    # 첫 성공
                    status.is_healthy = True
                    logger.info(f"[HealthCheck] {server_name} 정상 ({status.host}:{status.port})")

                    if self._on_status_change:
                        try:
                            await self._on_status_change(server_name, True, status)
                        except Exception as callback_error:
                            logger.error(
                                f"[HealthCheck] {server_name} 상태 변경 콜백 실행 실패: {callback_error}",
                                exc_info=True
                            )

            else:
                status.consecutive_failures += 1
                status.consecutive_successes = 0

                # 실패가 계속되면 unhealthy로 표시
                if was_healthy and status.consecutive_failures >= 2:
                    status.is_healthy = False
                    logger.warning(f"[HealthCheck] {server_name} 다운됨 (연속 실패: {status.consecutive_failures})")

                    # 상태 변경 콜백 호출
                    if self._on_status_change:
                        try:
                            await self._on_status_change(server_name, False, status)
                        except Exception as callback_error:
                            logger.error(
                                f"[HealthCheck] {server_name} 상태 변경 콜백 실행 실패: {callback_error}",
                                exc_info=True
                            )
                elif not was_healthy:
                    logger.debug(f"[HealthCheck] {server_name} 여전히 다운")
                else:
                    logger.warning(f"[HealthCheck] {server_name} 실패 (연속: {status.consecutive_failures})")

        except Exception as e:
            logger.error(f"[HealthCheck] {server_name} 체크 중 에러: {e}")

    def get_server_status(self, server_name: str) -> Optional[ServerHealthStatus]:
        """서버 상태 조회"""
        return self.server_statuses.get(server_name)

    def get_all_statuses(self) -> Dict[str, ServerHealthStatus]:
        """모든 서버 상태 조회"""
        return self.server_statuses.copy()

    def get_all_statuses_dict(self) -> dict:
        """모든 서버 상태를 딕셔너리로 반환"""
        return {
            name: status.to_dict()
            for name, status in self.server_statuses.items()
        }
