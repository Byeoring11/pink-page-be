# 에러 처리 가이드

## 목차
1. [개요](#개요)
2. [에러 코드 체계](#에러-코드-체계)
3. [커스텀 예외 사용법](#커스텀-예외-사용법)
4. [REST API 에러 처리](#rest-api-에러-처리)
5. [WebSocket 에러 처리](#websocket-에러-처리)
6. [로깅 전략](#로깅-전략)
7. [기존 코드 마이그레이션](#기존-코드-마이그레이션)

---

## 개요

본 프로젝트는 체계적인 에러 처리를 위해 다음과 같은 구조를 사용합니다:

- **에러 코드**: 5자리 숫자로 구성된 체계적인 코드
- **커스텀 예외**: 계층 구조를 가진 예외 클래스
- **전역 핸들러**: FastAPI/WebSocket 에러를 일관되게 처리
- **구조화된 로깅**: 에러 추적과 디버깅을 위한 상세 로깅

---

## 에러 코드 체계

### 코드 구조

에러 코드는 5자리 숫자로 구성됩니다:

```
[카테고리][서브카테고리][구체적 에러]
   1자리      2-3자리      4-5자리
```

### 카테고리

- **1XXXX**: 일반 에러 (인증, 유효성 검증, 리소스 등)
- **2XXXX**: SSH 관련 에러
- **3XXXX**: WebSocket 관련 에러
- **4XXXX**: 데이터베이스 에러
- **5XXXX**: 비즈니스 로직 에러

### 주요 에러 코드 예시

```python
# 일반 에러
10000  # 내부 서버 오류
11000  # 인증 필요
12000  # 유효성 검증 실패
13000  # 리소스를 찾을 수 없음

# SSH 에러
20000  # SSH 연결 실패
21000  # SSH 인증 실패
22000  # SSH 명령 실행 실패

# WebSocket 에러
30000  # WebSocket 연결 실패
31000  # 메시지 전송 실패
32000  # 핸들러를 찾을 수 없음

# 비즈니스 로직 에러
50000  # STUB 명령 실행 실패
51000  # BMX4 작업 실패
52000  # BMX5 작업 실패
53000  # DIFF 비교 실패
```

---

## 커스텀 예외 사용법

### 1. 기본 사용법

```python
from app.core.exceptions import SSHConnectionException
from app.core.error_codes import ErrorCode

# 간단한 예외 발생
raise SSHConnectionException(
    host="192.168.1.1",
    port=22,
    detail="연결 타임아웃"
)

# 에러 코드를 직접 지정
raise SSHAuthException(
    username="user",
    error_code=ErrorCode.SSH_AUTH_TIMEOUT
)
```

### 2. 예외 계층 구조

```
BaseAppException
├── GeneralException
│   ├── ValidationException
│   ├── ResourceNotFoundException
│   └── UnauthorizedException
├── SSHException
│   ├── SSHConnectionException
│   ├── SSHAuthException
│   ├── SSHCommandException
│   └── SSHTimeoutException
├── WebSocketException
│   ├── WSConnectionException
│   ├── WSMessageException
│   ├── WSInvalidMessageException
│   └── WSHandlerNotFoundException
├── DatabaseException
│   ├── DBConnectionException
│   └── DBQueryException
└── BusinessException
    ├── StubException
    │   ├── StubCommandFailedException
    │   ├── StubInvalidConnectionException
    │   └── StubSessionExpiredException
    ├── Bmx4Exception
    │   ├── Bmx4OperationFailedException
    │   └── Bmx4InvalidRequestException
    ├── Bmx5Exception
    │   ├── Bmx5OperationFailedException
    │   └── Bmx5InvalidRequestException
    └── DiffException
        ├── DiffComparisonFailedException
        └── DiffInvalidInputException
```

### 3. 컨텍스트 정보 추가

```python
from app.core.exceptions import BaseAppException
from app.core.error_codes import ErrorCode

raise BaseAppException(
    error_code=ErrorCode.SSH_COMMAND_FAILED,
    detail="명령 실행 중 오류 발생",
    context={
        "command": "ls -la",
        "server": "wdexgm1p",
        "exit_code": 1
    }
)
```

### 4. 원본 예외 래핑

```python
try:
    # Paramiko SSH 연결
    transport.auth_password(username, password)
except paramiko.AuthenticationException as e:
    raise SSHAuthException(
        username=username,
        detail="비밀번호 인증 실패",
        original_exception=e
    )
```

---

## REST API 에러 처리

### 1. Service 레이어에서 예외 발생

```python
# app/domains/stub/services/stub_service.py
from app.core.exceptions import StubCommandFailedException

class StubService:
    async def execute_command(self, command: str, connection_id: str):
        # 연결 확인
        if not self._is_connected(connection_id):
            raise StubCommandFailedException(
                command=command,
                detail=f"Not connected: {connection_id}"
            )

        # 명령 실행
        result = await self._run_command(command)
        return result
```

### 2. API 엔드포인트

```python
# app/api/v1/endpoints/stub.py
from fastapi import APIRouter, Depends
from app.domains.stub.services.stub_service import StubService

router = APIRouter()

@router.post("/commands/execute")
async def execute_command(
    command: str,
    connection_id: str,
    service: StubService = Depends()
):
    """
    명령 실행 엔드포인트

    예외는 전역 핸들러가 자동으로 처리하므로
    try-except 블록이 필요 없습니다.
    """
    # 예외가 발생하면 전역 핸들러가 자동으로 처리
    result = await service.execute_command(command, connection_id)

    return {
        "success": True,
        "data": result
    }
```

### 3. 클라이언트 응답 형식

**성공 응답:**
```json
{
  "success": true,
  "data": {
    "task_id": "12345",
    "status": "running"
  }
}
```

**에러 응답:**
```json
{
  "success": false,
  "error": {
    "code": 50000,
    "message": "Command execution failed",
    "detail": "Not connected: conn_123"
  },
  "path": "/api/v1/commands/execute"
}
```

---

## WebSocket 에러 처리

### 1. WebSocket 핸들러에서 예외 처리

#### 방법 1: 데코레이터 사용 (권장)

```python
from fastapi import WebSocket
from app.core.websocket_error_handler import handle_ws_errors

@handle_ws_errors(send_error=True, close_on_error=False)
async def handle_ssh_command(
    websocket: WebSocket,
    connection_id: str,
    data: dict
):
    """
    SSH 명령 핸들러

    예외가 발생하면 데코레이터가 자동으로:
    1. 에러 로깅
    2. 클라이언트에 에러 메시지 전송
    3. 연결 유지 (close_on_error=False)
    """
    command = data.get("command")

    # 예외가 발생하면 자동으로 처리됨
    result = await ssh_service.execute_command(command)

    await websocket.send_json({
        "type": "command_result",
        "data": result
    })
```

#### 방법 2: WebSocketErrorHandler 직접 사용

```python
from fastapi import WebSocket
from app.core.websocket_error_handler import WebSocketErrorHandler
from app.core.exceptions import StubCommandFailedException

async def handle_message(websocket: WebSocket, connection_id: str):
    handler = WebSocketErrorHandler(websocket, connection_id)

    try:
        # 메시지 처리 로직
        data = await websocket.receive_json()
        result = await process_message(data)

        await websocket.send_json({
            "type": "success",
            "data": result
        })

    except StubCommandFailedException as e:
        # 에러 메시지 전송하고 연결 유지
        await handler.handle_exception(
            e,
            send_to_client=True,
            close_connection=False
        )

    except Exception as e:
        # 심각한 에러: 메시지 전송하고 연결 종료
        await handler.handle_exception(
            e,
            send_to_client=True,
            close_connection=True
        )
```

#### 방법 3: 헬퍼 함수 사용

```python
from app.core.websocket_error_handler import create_error_message, send_error_and_close
from app.core.error_codes import ErrorCode

async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    await websocket.accept()

    try:
        # 연결 검증
        if not is_valid_connection(connection_id):
            # 에러 메시지 전송 후 연결 종료
            await send_error_and_close(
                websocket,
                ErrorCode.STUB_INVALID_CONNECTION_ID,
                detail=f"연결 ID '{connection_id}'가 유효하지 않습니다",
                connection_id=connection_id
            )
            return

        # 정상 처리
        while True:
            data = await websocket.receive_json()
            # ...

    except WebSocketDisconnect:
        logger.info(f"클라이언트 연결 해제: {connection_id}")
```

### 2. WebSocket 에러 메시지 형식

```json
{
  "type": "error",
  "success": false,
  "error": {
    "code": 51000,
    "message": "명령 실행에 실패했습니다",
    "detail": "서버 응답 타임아웃"
  },
  "timestamp": "2025-12-06T04:30:00.123456"
}
```

---

## 로깅 전략

### 1. 자동 로깅

모든 예외는 전역 핸들러가 자동으로 로깅합니다:

```python
# 예외만 발생시키면 됨
raise SSHConnectionException(host="192.168.1.1", detail="연결 실패")

# 자동 로그 출력:
# [ERROR] [WS:abc123] [20000] SSH 서버 연결에 실패했습니다
# {
#   "error_code": 20000,
#   "detail": "연결 실패",
#   "context": {"host": "192.168.1.1"},
#   "connection_id": "abc123"
# }
```

### 2. 추가 로깅

```python
from app.core.logger import logger

# 정보성 로그
logger.info(
    f"SSH 연결 시도: {host}:{port}",
    extra={
        "host": host,
        "port": port,
        "username": username
    }
)

# 경고 로그
logger.warning(
    f"재시도 {retry_count}/{max_retries}",
    extra={
        "retry_count": retry_count,
        "operation": "ssh_connect"
    }
)

# 에러 로그 (예외와 함께)
try:
    result = risky_operation()
except Exception as e:
    logger.error(
        f"작업 실패: {str(e)}",
        extra={
            "operation": "risky_operation",
            "error": str(e)
        },
        exc_info=True  # 스택 트레이스 포함
    )
    raise
```

### 3. 로깅 레벨 가이드

- **DEBUG**: 개발/디버깅용 상세 정보
- **INFO**: 정상 동작 흐름 (연결 성공, 작업 시작 등)
- **WARNING**: 주의가 필요한 상황 (재시도, 4XX 에러 등)
- **ERROR**: 오류 상황 (5XX 에러, 예외 등)
- **CRITICAL**: 시스템 전체에 영향을 주는 심각한 오류

---

## 기존 코드 마이그레이션

### Before (기존 코드)

```python
# ❌ 기존 방식: 직접 raise, 수동 로깅, 불명확한 에러
async def connect_ssh(host: str, username: str, password: str):
    try:
        transport = paramiko.Transport((host, 22))
        transport.auth_password(username, password)
        logger.info("SSH connection successful")
        return transport
    except Exception as e:
        logger.error(f"SSH connection failed: {str(e)}")
        raise Exception(f"Failed to connect to {host}")
```

### After (개선된 코드)

```python
# ✅ 개선 방식: 체계적인 예외, 자동 로깅, 명확한 에러 코드
from app.core.exceptions import SSHConnectionException, SSHAuthException
from app.core.logger import logger

async def connect_ssh(host: str, username: str, password: str):
    try:
        transport = paramiko.Transport((host, 22))
        logger.info(f"SSH 연결 시도: {host}", extra={"host": host})

        transport.auth_password(username, password)
        logger.info(f"SSH 연결 성공: {host}", extra={"host": host})

        return transport

    except paramiko.AuthenticationException as e:
        # 인증 실패: 자동으로 로깅되고 클라이언트에 명확한 에러 코드 전달
        raise SSHAuthException(
            username=username,
            detail="비밀번호 인증 실패",
            original_exception=e
        )

    except socket.timeout as e:
        raise SSHConnectionException(
            host=host,
            port=22,
            detail="연결 타임아웃",
            error_code=ErrorCode.SSH_CONNECTION_TIMEOUT,
            original_exception=e
        )

    except Exception as e:
        raise SSHConnectionException(
            host=host,
            port=22,
            detail=str(e),
            original_exception=e
        )
```

### 마이그레이션 체크리스트

1. **일반 Exception 제거**
   - ❌ `raise Exception("error")`
   - ✅ `raise SSHConnectionException(detail="error")`

2. **수동 로깅 제거**
   - ❌ `logger.error("error"); raise Exception("error")`
   - ✅ `raise SSHConnectionException(detail="error")`  # 자동 로깅됨

3. **에러 메시지 하드코딩 제거**
   - ❌ `raise Exception("SSH connection failed")`
   - ✅ `raise SSHConnectionException()`  # 메시지는 ErrorCode에 정의됨

4. **try-except 단순화**
   - API 엔드포인트에서는 try-except 불필요 (전역 핸들러가 처리)
   - Service 레이어에서만 예외 변환 필요

5. **컨텍스트 정보 추가**
   - 디버깅에 유용한 정보를 `context`에 포함
   - 민감한 정보(비밀번호 등)는 제외

---

## 예제: 완전한 구현

### Service 레이어

```python
# app/domains/stub/services/stub_ssh_service.py
from app.core.exceptions import (
    SSHConnectionException,
    SSHAuthException,
    SSHCommandException,
    SSHTimeoutException
)
from app.core.error_codes import ErrorCode
from app.core.logger import logger

class StubSSHService:
    async def connect(self, host: str, username: str, password: str) -> bool:
        """SSH 서버 연결"""
        try:
            sock = socket.create_connection((host, 22), timeout=10)
            logger.info(f"TCP 연결 성공: {host}")

            self.transport = paramiko.Transport(sock)
            self.transport.start_client()
            logger.info(f"SSH 클라이언트 시작: {host}")

            # 인증
            try:
                self.transport.auth_password(username, password)
                logger.info(f"SSH 인증 성공: {username}@{host}")
                self.is_connected = True
                return True

            except paramiko.AuthenticationException as e:
                raise SSHAuthException(
                    username=username,
                    detail="비밀번호 인증 실패",
                    original_exception=e
                )

        except socket.timeout as e:
            raise SSHConnectionException(
                host=host,
                port=22,
                error_code=ErrorCode.SSH_CONNECTION_TIMEOUT,
                detail=f"{host} 연결 타임아웃 (10초)",
                original_exception=e
            )

        except Exception as e:
            raise SSHConnectionException(
                host=host,
                port=22,
                detail=f"연결 실패: {str(e)}",
                original_exception=e
            )

    async def execute_command(
        self,
        command: str,
        timeout: float = 30.0
    ) -> str:
        """명령 실행"""
        if not self.is_connected:
            raise SSHConnectionException(
                error_code=ErrorCode.SSH_NOT_CONNECTED,
                detail="SSH 연결이 되어있지 않습니다"
            )

        try:
            # 명령 실행 로직
            result = await self._run_command(command, timeout)
            return result

        except asyncio.TimeoutError:
            raise SSHTimeoutException(
                timeout_seconds=timeout,
                operation=f"command: {command}",
                context={"command": command}
            )

        except Exception as e:
            raise SSHCommandException(
                command=command,
                detail=f"명령 실행 실패: {str(e)}",
                original_exception=e
            )
```

### WebSocket 엔드포인트

```python
# app/api/v1/websockets/stub.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_error_handler import WebSocketErrorHandler, handle_ws_errors
from app.domains.stub.services.stub_ssh_service import StubSSHService

router = APIRouter()

@router.websocket("/stub/{connection_id}")
async def stub_websocket(websocket: WebSocket, connection_id: str):
    """STUB WebSocket 엔드포인트"""
    await websocket.accept()

    error_handler = WebSocketErrorHandler(websocket, connection_id)
    ssh_service = StubSSHService()

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "ssh_connect":
                await handle_ssh_connect(
                    websocket,
                    connection_id,
                    ssh_service,
                    data,
                    error_handler
                )

            elif message_type == "ssh_command":
                await handle_ssh_command(
                    websocket,
                    connection_id,
                    ssh_service,
                    data,
                    error_handler
                )

    except WebSocketDisconnect:
        logger.info(f"클라이언트 연결 해제: {connection_id}")
        await ssh_service.disconnect()


@handle_ws_errors(send_error=True, close_on_error=False)
async def handle_ssh_connect(
    websocket: WebSocket,
    connection_id: str,
    ssh_service: StubSSHService,
    data: dict,
    error_handler: WebSocketErrorHandler
):
    """SSH 연결 핸들러"""
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")

    # 예외가 발생하면 데코레이터가 자동 처리
    await ssh_service.connect(host, username, password)

    await websocket.send_json({
        "type": "ssh_connected",
        "success": True,
        "data": {"host": host}
    })


@handle_ws_errors(send_error=True, close_on_error=False)
async def handle_ssh_command(
    websocket: WebSocket,
    connection_id: str,
    ssh_service: StubSSHService,
    data: dict,
    error_handler: WebSocketErrorHandler
):
    """SSH 명령 핸들러"""
    command = data.get("command")

    # 예외가 발생하면 데코레이터가 자동 처리
    result = await ssh_service.execute_command(command)

    await websocket.send_json({
        "type": "command_result",
        "success": True,
        "data": {"output": result}
    })
```

---

## 요약

### 핵심 원칙

1. **명확한 에러 코드**: 클라이언트가 에러를 쉽게 식별하고 처리할 수 있도록
2. **계층적 예외**: 예외 타입으로 에러 카테고리를 쉽게 파악
3. **자동 처리**: 전역 핸들러가 로깅과 응답 생성을 자동으로 처리
4. **풍부한 컨텍스트**: 디버깅에 필요한 충분한 정보 제공
5. **일관성**: REST API와 WebSocket 모두 동일한 에러 구조 사용

### 개발 워크플로우

1. 적절한 예외 클래스 선택
2. 필요시 `detail`과 `context` 추가
3. 예외 발생 (전역 핸들러가 자동으로 처리)
4. 필요한 경우에만 로깅 추가 (대부분 자동)

이 가이드를 따르면 체계적이고 일관된 에러 처리가 가능합니다!
