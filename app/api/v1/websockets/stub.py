from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logger import logger
from app.infrastructures.websocketV2.connection_manager import WebSocketManager, WebSocketHandler
from app.domains.stub.services.stub_ssh_service import StubSSHService
from app.domains.stub.services.health_check_service import HealthCheckService, ServerHealthStatus
from app.core.exceptions import (
    StubSessionAlreadyActiveException,
    StubSessionNotActiveException,
    StubSessionPermissionDeniedException,
    StubResourceLockedException,
    StubTransferFailedException,
    WSBroadcastException,
)
import uuid
import asyncio


# 전역 인스턴스
ws_manager = WebSocketManager()
ws_handler = WebSocketHandler(ws_manager)
router = APIRouter()

# Health Check 서비스 (전역 싱글톤)
health_check_service = HealthCheckService(
    check_interval=30.0,  # 30초마다 체크
    timeout=5.0
)


# Health check 상태 변경 콜백
async def on_server_health_change(server_name: str, is_healthy: bool, status: ServerHealthStatus):
    """
    서버 health 상태 변경 시 모든 클라이언트에게 브로드캐스트
    """
    logger.info(f"[HealthCheck] {server_name} 상태 변경: {'정상' if is_healthy else '다운'}")

    try:
        # 모든 WebSocket 클라이언트에게 브로드캐스트
        success_count = await ws_manager.broadcast_json({
            "type": "server_health",
            "server_name": server_name,
            "is_healthy": is_healthy,
            "status": status.to_dict()
        })
        logger.debug(f"[HealthCheck] Health 상태 브로드캐스트 완료: {success_count}개 클라이언트")
    except WSBroadcastException as e:
        logger.warning(f"[HealthCheck] Health 상태 브로드캐스트 실패: {e}")
        # 브로드캐스트 실패는 health check를 중단하지 않음
    except Exception as e:
        logger.error(f"[HealthCheck] Health 상태 브로드캐스트 중 예상치 못한 에러: {e}", exc_info=True)


# 콜백 등록
health_check_service.set_status_change_callback(on_server_health_change)


class StubWebSocketController:
    """대응답 적재 기능을 위한 컨트롤러 클래스"""

    def __init__(self):
        self.ssh_services = {}  # connection_id -> StubSSHService
        self.is_locked = False  # SSH 작업 점유 여부
        self.lock_owner_id = None  # 현재 점유 중인 connection_id
        self.session_active = False  # 세션 활성화 여부
        self.session_owner_id = None  # 세션 소유자 connection_id

    async def handle_start_session(self, connection_id: str, data: dict):
        """
        세션 시작 핸들러
        세션을 시작하면 해당 connection_id만 작업을 수행할 수 있음
        """
        try:
            if self.session_active:
                raise StubSessionAlreadyActiveException(
                    session_owner=self.session_owner_id
                )
        except StubSessionAlreadyActiveException as e:
            logger.warning(f"[STUB] {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": e.error_code.message,
                "detail": e.detail,
                "error_code": e.code,
                "session_active": True,
                "session_owner": self.session_owner_id
            })
            return

        # 세션 시작
        self.session_active = True
        self.session_owner_id = connection_id
        logger.info(f"[STUB] Session started by {connection_id}")

        # 클라이언트에게 세션 시작 응답
        await ws_manager.send_json(connection_id, {
            "type": "session_started",
            "message": "Session started successfully",
            "session_owner": connection_id
        })

        # 모든 클라이언트에게 세션 시작 브로드캐스트
        await ws_manager.broadcast_json({
            "type": "session_status",
            "session_active": True,
            "session_owner": connection_id,
            "message": f"Session started by client {connection_id}"
        })

    async def handle_end_session(self, connection_id: str, data: dict):
        """
        세션 종료 핸들러
        """
        try:
            if not self.session_active:
                raise StubSessionNotActiveException(
                    detail="No active session to end"
                )

            if self.session_owner_id != connection_id:
                raise StubSessionPermissionDeniedException(
                    session_owner=self.session_owner_id,
                    requester=connection_id
                )
        except (StubSessionNotActiveException, StubSessionPermissionDeniedException) as e:
            logger.warning(f"[STUB] {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": e.error_code.message,
                "detail": e.detail,
                "error_code": e.code
            })
            return

        # 세션 종료
        self.session_active = False
        self.session_owner_id = None
        logger.info(f"[STUB] Session ended by {connection_id}")

        # 클라이언트에게 세션 종료 응답
        await ws_manager.send_json(connection_id, {
            "type": "session_ended",
            "message": "Session ended successfully"
        })

        # 모든 클라이언트에게 세션 종료 브로드캐스트
        await ws_manager.broadcast_json({
            "type": "session_status",
            "session_active": False,
            "session_owner": None,
            "message": "Session ended"
        })

    def _check_session_permission(self, connection_id: str) -> bool:
        """
        세션 권한 확인
        세션이 활성화되어 있으면 세션 소유자만 작업 가능
        """
        if self.session_active and self.session_owner_id != connection_id:
            return False
        return True

    async def handle_ssh_command(self, connection_id: str, data: dict):
        """
        웹소켓 메세지 'ssh_command' 수신 시 핸들러
        data dictionary 안에 담긴 'server'에 SSH 연결하여 인터랙티브 쉘을 통해 'command' 실행
        """
        try:
            # 세션 권한 확인
            if not self._check_session_permission(connection_id):
                raise StubSessionPermissionDeniedException(
                    session_owner=self.session_owner_id,
                    requester=connection_id
                )
        except StubSessionPermissionDeniedException as e:
            logger.warning(f"[STUB] {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": e.error_code.message,
                "detail": e.detail,
                "error_code": e.code,
                "session_active": True,
                "session_owner": self.session_owner_id
            })
            return

        try:

            server_name = data.get("server", "")
            command = data.get("command", "")
            throttle_interval = data.get("throttle_interval", 0.1)  # 기본값 0.1초

            # 종료 문자열 정의
            stop_phrase = "[SUCC] PostgreSQL load data unload Process"  # mdwap1p 서버 대응답 Shell 종료 문자열
            if not all([server_name, command]):
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": "Missing required fields: server, command"
                })
                return

            # 세션이 없는 경우에만 락 획득 시도 (세션이 있으면 이미 권한 확인됨)
            if not self.session_active:
                try:
                    if self.is_locked:
                        raise StubResourceLockedException(
                            lock_owner=self.lock_owner_id,
                            resource="SSH service"
                        )
                except StubResourceLockedException as e:
                    logger.warning(f"[STUB] {e}")
                    await ws_manager.send_json(connection_id, {
                        "type": "error",
                        "message": e.error_code.message,
                        "detail": e.detail,
                        "error_code": e.code,
                        "locked": True,
                        "lock_owner": self.lock_owner_id
                    })
                    return

                # 락 획득 성공
                self.is_locked = True
                self.lock_owner_id = connection_id
                logger.info(f"[STUB] SSH lock acquired by {connection_id}")

                # 모든 클라이언트에게 작업 시작 브로드캐스트
                await ws_manager.broadcast_json({
                    "type": "lock_status",
                    "locked": True,
                    "lock_owner": connection_id,
                    "message": f"SSH service locked by client {connection_id}"
                })

            # Stub SSH Service 인스턴스 생성
            ssh_service = StubSSHService()
            self.ssh_services[connection_id] = ssh_service

            # 인터랙티브 쉘의 출력 결과를 웹소켓을 통해 클라이언트단으로 보내는 output_callback 함수 정의하여 세팅
            # Set output callback to send data to WebSocket
            async def output_callback(output: str):
                await ws_manager.send_json(connection_id, {
                    "type": "output",
                    "data": output
                })

            ssh_service.set_output_callback(output_callback)

            # Get server configuration
            try:
                host, username, password = ssh_service.get_server_config(server_name)
            except ValueError as e:
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": str(e)
                })
                return

            # Send connection status
            await ws_manager.send_json(connection_id, {
                "type": "status",
                "message": f"Connecting to {server_name}..."
            })

            # Connect to SSH server
            connected = await ssh_service.connect(host, username, password)
            if not connected:
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": "Failed to connect to SSH server"
                })
                return

            await ws_manager.send_json(connection_id, {
                "type": "status",
                "message": "Connected! Starting interactive shell..."
            })

            # Start interactive shell with command and throttling
            await ssh_service.start_interactive_shell(
                command=command,
                stop_phrase=stop_phrase,
                throttle_interval=throttle_interval
            )

            # Send completion status
            await ws_manager.send_json(connection_id, {
                "type": "complete",
                "message": "Command execution completed"
            })

        except Exception as e:
            logger.error(f"Error handling SSH command: {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": f"SSH command execution failed: {str(e)}"
            })
        finally:
            # Clean up SSH service
            if connection_id in self.ssh_services:
                await self.ssh_services[connection_id].disconnect()
                del self.ssh_services[connection_id]

            # 락 해제 (세션이 없는 경우에만)
            if not self.session_active and self.lock_owner_id == connection_id:
                self.is_locked = False
                self.lock_owner_id = None
                logger.info(f"[STUB] SSH lock released by {connection_id}")

                # 모든 클라이언트에게 작업 종료 브로드캐스트
                await ws_manager.broadcast_json({
                    "type": "lock_status",
                    "locked": False,
                    "lock_owner": None,
                    "message": "SSH service is now available"
                })

    async def handle_ssh_input(self, connection_id: str, data: dict):
        """
        웹소켓 메세지 'ssh_input' 수신 시 핸들러
        data dictionary 안에 담긴 'input'을 인터랙티브 쉘을 통해 'command' 실행
        SSH 세션에 유저의 입력값을 발신
        """
        try:
            input_text = data.get("input", "")

            if connection_id in self.ssh_services:
                await self.ssh_services[connection_id].send_input(input_text)
            else:
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": "No active SSH session"
                })

        except Exception as e:
            logger.error(f"Error handling SSH input: {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": f"Failed to send input: {str(e)}"
            })

    async def handle_scp_transfer(self, connection_id: str, data: dict):
        """
        SCP 파일 전송 핸들러
        설정된 경로로 원격 서버 간 파일 전송 (mdwap1p → mypap1d)

        data 형식:
        {
            "transfer_name": "stub_data_transfer"  # optional, default: "stub_data_transfer"
        }
        """
        try:
            # 세션 권한 확인
            if not self._check_session_permission(connection_id):
                raise StubSessionPermissionDeniedException(
                    session_owner=self.session_owner_id,
                    requester=connection_id
                )
        except StubSessionPermissionDeniedException as e:
            logger.warning(f"[STUB] {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": e.error_code.message,
                "detail": e.detail,
                "error_code": e.code,
                "session_active": True,
                "session_owner": self.session_owner_id
            })
            return

        try:

            transfer_name = data.get("transfer_name", "stub_data_transfer")

            await ws_manager.send_json(connection_id, {
                "type": "status",
                "message": f"Starting SCP transfer: {transfer_name}"
            })

            # StubSSHService 인스턴스 생성
            ssh_service = StubSSHService()

            # 출력 콜백 함수 정의
            async def output_callback(output: str):
                await ws_manager.send_json(connection_id, {
                    "type": "output",
                    "data": output
                })

            # SCP 전송 수행
            success = await ssh_service.scp_transfer(
                transfer_name=transfer_name,
                output_callback=output_callback
            )

            if success:
                await ws_manager.send_json(connection_id, {
                    "type": "complete",
                    "message": "SCP transfer completed successfully"
                })
            else:
                raise StubTransferFailedException(
                    transfer_name=transfer_name,
                    detail="SCP transfer failed"
                )

        except StubTransferFailedException as e:
            logger.error(f"[STUB] {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": e.error_code.message,
                "detail": e.detail,
                "error_code": e.code
            })
        except Exception as e:
            logger.error(f"[STUB] Unexpected error in SCP transfer: {e}")
            transfer_exc = StubTransferFailedException(
                transfer_name=transfer_name,
                detail=str(e)
            )
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": transfer_exc.error_code.message,
                "detail": transfer_exc.detail,
                "error_code": transfer_exc.code
            })

    async def handle_get_lock_status(self, connection_id: str, data: dict):
        """
        현재 락 상태를 조회하는 핸들러
        """
        await ws_manager.send_json(connection_id, {
            "type": "lock_status",
            "locked": self.is_locked,
            "lock_owner": self.lock_owner_id,
            "message": f"Locked by {self.lock_owner_id}" if self.is_locked else "Available"
        })

    async def handle_disconnect(self, connection_id: str):
        """Handle WebSocket disconnect"""
        if connection_id in self.ssh_services:
            await self.ssh_services[connection_id].disconnect()
            del self.ssh_services[connection_id]
            logger.info(f"Cleaned up SSH service for connection: {connection_id}")

        # 연결 해제 시 해당 클라이언트가 세션을 소유하고 있었다면 세션 및 락 해제
        if self.session_owner_id == connection_id:
            self.session_active = False
            self.session_owner_id = None
            logger.info(f"[STUB] Session released due to disconnect: {connection_id}")

            # 모든 클라이언트에게 세션 해제 브로드캐스트
            await ws_manager.broadcast_json({
                "type": "session_status",
                "session_active": False,
                "session_owner": None,
                "message": "Session ended (owner disconnected)"
            })

        # 연결 해제 시 해당 클라이언트가 락을 소유하고 있었다면 락 해제
        if self.lock_owner_id == connection_id:
            self.is_locked = False
            self.lock_owner_id = None
            logger.info(f"[STUB] SSH lock released due to disconnect: {connection_id}")

            # 모든 클라이언트에게 락 해제 브로드캐스트
            await ws_manager.broadcast_json({
                "type": "lock_status",
                "locked": False,
                "lock_owner": None,
                "message": "SSH service is now available (previous owner disconnected)"
            })


# Controller 인스턴스 생성
stub_controller = StubWebSocketController()


# 메세지 핸들러 등록
@ws_handler.on_message("ssh_command")
async def handle_ssh_command(connection_id: str, data: dict):
    """Handle SSH command execution"""
    await stub_controller.handle_ssh_command(connection_id, data)


@ws_handler.on_message("ssh_input")
async def handle_ssh_input(connection_id: str, data: dict):
    """Handle SSH input"""
    await stub_controller.handle_ssh_input(connection_id, data)


@ws_handler.on_message("get_lock_status")
async def handle_get_lock_status(connection_id: str, data: dict):
    """Handle lock status query"""
    await stub_controller.handle_get_lock_status(connection_id, data)


@ws_handler.on_message("start_session")
async def handle_start_session(connection_id: str, data: dict):
    """Handle session start"""
    await stub_controller.handle_start_session(connection_id, data)


@ws_handler.on_message("end_session")
async def handle_end_session(connection_id: str, data: dict):
    """Handle session end"""
    await stub_controller.handle_end_session(connection_id, data)


@ws_handler.on_message("scp_transfer")
async def handle_scp_transfer(connection_id: str, data: dict):
    """Handle SCP file transfer"""
    await stub_controller.handle_scp_transfer(connection_id, data)


@ws_handler.on_connect("connect")
async def handle_connect(connection_id: str):
    """Handle WebSocket connection"""
    # Welcome 메시지와 함께 현재 락, 세션, 서버 health 상태 전송
    await ws_manager.send_json(connection_id, {
        "type": "welcome",
        "message": "Connected to Stub SSH WebSocket",
        "connection_id": connection_id,
        "lock_status": {
            "locked": stub_controller.is_locked,
            "lock_owner": stub_controller.lock_owner_id
        },
        "session_status": {
            "active": stub_controller.session_active,
            "owner": stub_controller.session_owner_id
        },
        "server_health": health_check_service.get_all_statuses_dict()
    })


@ws_handler.on_connect("disconnect")
async def handle_disconnect(connection_id: str):
    """Handle WebSocket disconnection"""
    await stub_controller.handle_disconnect(connection_id)


@router.websocket("/stub")
async def stub_websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for stub functionality"""
    # 서버에서 자동으로 고유한 connection_id 생성
    connection_id = str(uuid.uuid4())
    logger.info(f"New WebSocket connection with ID: {connection_id}")

    try:
        # Handle the WebSocket connection using our handler
        await ws_handler.handle_connection(websocket, connection_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Closing WebSocket error for {connection_id}: {e}")
            pass
