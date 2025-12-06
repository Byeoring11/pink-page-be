"""
에러 처리 사용 예제

이 파일은 새로운 에러 처리 시스템의 사용법을 보여줍니다.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List

from app.core.exceptions import (
    SSHConnectionException,
    SSHAuthException,
    SSHCommandException,
    StubCommandFailedException,
    ValidationException,
    ResourceNotFoundException,
    ErrorCode,
    WebSocketErrorHandler,
    handle_ws_errors,
    create_error_message,
    send_error_and_close,
)
from app.core.logger import logger


# ============================================
# 예제 1: REST API 에러 처리
# ============================================

router = APIRouter()


@router.post("/commands/execute")
async def execute_command_endpoint(command: str, connection_id: str):
    """
    명령 실행 엔드포인트

    예외가 발생하면 전역 핸들러가 자동으로:
    1. 적절한 HTTP 상태 코드로 응답
    2. 표준 JSON 에러 형식으로 변환
    3. 에러 로깅
    """
    # 유효성 검증
    if not command:
        raise ValidationException(
            detail="Command is required",
            field="command"
        )

    if not connection_id:
        raise ValidationException(
            detail="Connection ID is required",
            field="connection_id"
        )

    # 비즈니스 로직 (예외가 발생하면 자동으로 처리됨)
    result = await execute_command(command, connection_id)

    return {
        "success": True,
        "data": {"result": result}
    }


async def execute_command(command: str, connection_id: str) -> str:
    """
    실제 명령 실행 로직 (Service 레이어)
    """
    # 연결 확인
    if not is_connection_valid(connection_id):
        raise StubCommandFailedException(
            command=command,
            detail=f"Invalid connection: {connection_id}"
        )

    # 명령 실행
    logger.info(f"Executing command: {command}", extra={"connection_id": connection_id})
    result = f"Command '{command}' executed successfully"

    return result


def is_connection_valid(connection_id: str) -> bool:
    """연결 유효성 확인 (더미)"""
    return True


# ============================================
# 예제 2: SSH 연결 에러 처리
# ============================================

async def connect_to_ssh_server(host: str, username: str, password: str):
    """
    SSH 서버 연결 예제

    다양한 예외 상황을 체계적으로 처리합니다.
    """
    import socket
    import paramiko

    try:
        # TCP 연결
        logger.info(f"SSH 연결 시도: {username}@{host}")

        sock = socket.create_connection((host, 22), timeout=10)
        transport = paramiko.Transport(sock)
        transport.start_client()

        # 인증
        try:
            transport.auth_password(username, password)
            logger.info(f"SSH 인증 성공: {username}@{host}")
            return transport

        except paramiko.AuthenticationException as e:
            raise SSHAuthException(
                username=username,
                detail="비밀번호 인증 실패",
                original_exception=e
            )

        except paramiko.SSHException as e:
            raise SSHAuthException(
                username=username,
                error_code=ErrorCode.SSH_AUTH_TIMEOUT,
                detail=str(e),
                original_exception=e
            )

    except socket.timeout as e:
        raise SSHConnectionException(
            host=host,
            port=22,
            error_code=ErrorCode.SSH_CONNECTION_TIMEOUT,
            detail="연결 타임아웃 (10초)",
            original_exception=e
        )

    except socket.error as e:
        raise SSHConnectionException(
            host=host,
            port=22,
            error_code=ErrorCode.SSH_CONNECTION_REFUSED,
            detail=f"연결 거부: {str(e)}",
            original_exception=e
        )

    except Exception as e:
        raise SSHConnectionException(
            host=host,
            port=22,
            detail=f"알 수 없는 오류: {str(e)}",
            original_exception=e
        )


# ============================================
# 예제 3: SSH 명령 실행 에러 처리
# ============================================

async def execute_ssh_command(transport, command: str, timeout: float = 30.0):
    """
    SSH 명령 실행 예제
    """
    import asyncio

    try:
        logger.info(f"명령 실행: {command}")

        # 명령 실행 (비동기 타임아웃 포함)
        result = await asyncio.wait_for(
            run_command(transport, command),
            timeout=timeout
        )

        logger.info(f"명령 실행 성공: {command}")
        return result

    except asyncio.TimeoutError:
        raise SSHCommandException(
            command=command,
            error_code=ErrorCode.SSH_COMMAND_TIMEOUT,
            detail=f"명령 실행 타임아웃 ({timeout}초)",
            context={
                "timeout": timeout,
                "command": command
            }
        )

    except Exception as e:
        raise SSHCommandException(
            command=command,
            detail=f"명령 실행 실패: {str(e)}",
            original_exception=e
        )


async def run_command(transport, command: str) -> str:
    """명령 실행 (더미)"""
    return "command output"


# ============================================
# 예제 4: WebSocket 에러 처리 - 데코레이터 사용
# ============================================

@router.websocket("/ws/example1/{connection_id}")
async def websocket_example1(websocket: WebSocket, connection_id: str):
    """
    WebSocket 예제 1: 데코레이터를 사용한 에러 처리

    @handle_ws_errors 데코레이터가 자동으로:
    1. 예외 로깅
    2. 클라이언트에 에러 메시지 전송
    3. 연결 관리 (유지 또는 종료)
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "ping":
                await handle_ping(websocket, connection_id, data)

            elif message_type == "command":
                await handle_command(websocket, connection_id, data)

    except WebSocketDisconnect:
        logger.info(f"클라이언트 연결 해제: {connection_id}")


@handle_ws_errors(send_error=True, close_on_error=False)
async def handle_ping(websocket: WebSocket, connection_id: str, data: dict):
    """
    Ping 핸들러

    예외가 발생하면 데코레이터가:
    - 에러 메시지를 클라이언트에 전송
    - 연결은 유지 (close_on_error=False)
    """
    await websocket.send_json({
        "type": "pong",
        "timestamp": data.get("timestamp")
    })


@handle_ws_errors(send_error=True, close_on_error=False)
async def handle_command(websocket: WebSocket, connection_id: str, data: dict):
    """
    명령 핸들러

    예외가 발생하면 자동으로 처리됨
    """
    command = data.get("command")

    # SSH 명령 실행 (예외가 발생할 수 있음)
    # 예외가 발생하면 데코레이터가 자동으로 처리
    result = await execute_command_dummy(command)

    await websocket.send_json({
        "type": "command_result",
        "success": True,
        "data": {"output": result}
    })


async def execute_command_dummy(command: str) -> str:
    """명령 실행 더미 함수"""
    if command == "fail":
        raise SSHCommandException(
            command=command,
            detail="테스트 실패"
        )
    return f"Executed: {command}"


# ============================================
# 예제 5: WebSocket 에러 처리 - 수동 처리
# ============================================

@router.websocket("/ws/example2/{connection_id}")
async def websocket_example2(websocket: WebSocket, connection_id: str):
    """
    WebSocket 예제 2: WebSocketErrorHandler를 직접 사용

    더 세밀한 에러 처리가 필요한 경우
    """
    await websocket.accept()

    error_handler = WebSocketErrorHandler(websocket, connection_id)

    try:
        # 연결 검증
        if not is_valid_connection_id(connection_id):
            # 에러 메시지 전송 후 연결 종료
            await send_error_and_close(
                websocket,
                ErrorCode.STUB_INVALID_CONNECTION_ID,
                detail=f"유효하지 않은 연결 ID: {connection_id}",
                connection_id=connection_id
            )
            return

        while True:
            data = await websocket.receive_json()

            try:
                # 메시지 처리
                result = await process_message(data)

                await websocket.send_json({
                    "type": "success",
                    "data": result
                })

            except ValidationException as e:
                # 유효성 검증 실패: 에러 메시지만 전송, 연결 유지
                await error_handler.handle_exception(
                    e,
                    send_to_client=True,
                    close_connection=False
                )

            except SSHCommandException as e:
                # SSH 명령 실패: 에러 메시지 전송, 연결 유지
                await error_handler.handle_exception(
                    e,
                    send_to_client=True,
                    close_connection=False
                )

            except Exception as e:
                # 심각한 에러: 에러 메시지 전송 후 연결 종료
                await error_handler.handle_exception(
                    e,
                    send_to_client=True,
                    close_connection=True
                )
                break

    except WebSocketDisconnect:
        logger.info(f"클라이언트 연결 해제: {connection_id}")


def is_valid_connection_id(connection_id: str) -> bool:
    """연결 ID 검증 (더미)"""
    return len(connection_id) > 0


async def process_message(data: dict) -> dict:
    """메시지 처리 (더미)"""
    message_type = data.get("type")

    if not message_type:
        raise ValidationException(
            field="type",
            detail="메시지 타입이 필요합니다"
        )

    return {"processed": True}


# ============================================
# 예제 6: 에러 메시지 직접 생성
# ============================================

@router.websocket("/ws/example3/{connection_id}")
async def websocket_example3(websocket: WebSocket, connection_id: str):
    """
    WebSocket 예제 3: 에러 메시지를 직접 생성하고 전송

    가장 세밀한 제어가 필요한 경우
    """
    await websocket.accept()

    try:
        # 인증 확인
        auth_token = await websocket.receive_text()

        if not validate_auth_token(auth_token):
            # 에러 메시지 직접 생성
            error_message = create_error_message(
                ErrorCode.UNAUTHORIZED,
                detail="유효하지 않은 인증 토큰",
                connection_id=connection_id
            )

            # 에러 메시지 전송
            await websocket.send_json(error_message)

            # 연결 종료
            await websocket.close(code=1008, reason="Authentication failed")
            return

        # 정상 처리
        while True:
            data = await websocket.receive_json()
            # ...

    except WebSocketDisconnect:
        logger.info(f"클라이언트 연결 해제: {connection_id}")


def validate_auth_token(token: str) -> bool:
    """인증 토큰 검증 (더미)"""
    return token == "valid_token"


# ============================================
# 예제 7: 리소스를 찾을 수 없음 에러
# ============================================

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """
    사용자 조회 엔드포인트

    리소스를 찾을 수 없는 경우 404 에러 반환
    """
    user = await find_user(user_id)

    if not user:
        raise ResourceNotFoundException(
            resource_type="User",
            resource_id=user_id
        )

    return {
        "success": True,
        "data": user
    }


async def find_user(user_id: str):
    """사용자 조회 (더미)"""
    # 실제로는 데이터베이스 조회
    return None


# ============================================
# 예제 8: 컨텍스트 정보를 포함한 예외
# ============================================

async def process_batch_task(server_type: int, cusno_list: List[str]):
    """
    배치 작업 처리 예제

    에러 발생 시 디버깅에 유용한 컨텍스트 정보 포함
    """
    from app.core.exceptions import BaseAppException

    total = len(cusno_list)
    processed = 0
    failed = []

    try:
        for cusno in cusno_list:
            try:
                await process_single_cusno(server_type, cusno)
                processed += 1

            except Exception as e:
                failed.append(cusno)
                logger.error(
                    f"고객번호 처리 실패: {cusno}",
                    extra={"cusno": cusno, "error": str(e)}
                )

        if failed:
            raise BaseAppException(
                error_code=ErrorCode.DEUD_TASK_NOT_FOUND,  # 적절한 에러 코드 사용
                detail=f"{len(failed)}개 항목 처리 실패",
                context={
                    "total": total,
                    "processed": processed,
                    "failed": failed,
                    "failed_count": len(failed),
                    "success_rate": processed / total * 100
                }
            )

        logger.info(f"배치 작업 완료: {processed}/{total} 성공")

    except BaseAppException:
        raise  # 이미 처리된 예외는 그대로 전파

    except Exception as e:
        raise BaseAppException(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            detail=f"배치 작업 중 예기치 않은 오류: {str(e)}",
            context={
                "total": total,
                "processed": processed,
                "failed": failed
            },
            original_exception=e
        )


async def process_single_cusno(server_type: int, cusno: str):
    """단일 고객번호 처리 (더미)"""
    pass


# ============================================
# 사용법 요약
# ============================================

"""
## REST API

1. Service 레이어에서 적절한 예외 발생
2. 전역 핸들러가 자동으로:
   - HTTP 상태 코드 설정
   - JSON 응답 생성
   - 에러 로깅

## WebSocket

방법 1: @handle_ws_errors 데코레이터 (권장)
- 간단하고 깔끔
- 대부분의 경우에 적합

방법 2: WebSocketErrorHandler 직접 사용
- 세밀한 제어 필요시
- 에러 타입별로 다른 처리 필요시

방법 3: create_error_message + 수동 전송
- 가장 세밀한 제어
- 특수한 경우에만 사용

## 로깅

- 예외 발생 시 자동 로깅됨
- 추가 정보가 필요한 경우에만 수동 로깅
- context 파라미터로 디버깅 정보 제공

## 핵심 원칙

1. 명확한 예외 클래스 사용
2. detail로 상세 정보 제공
3. context로 디버깅 정보 추가
4. 전역 핸들러에 맡기기 (try-except 최소화)
"""
