# Pink-Page Backend (FastAPI)

FastAPI 기반의 SSH 원격 서버 제어 및 실시간 WebSocket 통신을 제공하는 백엔드 서비스입니다.

## 주요 기능

- **WebSocket 기반 실시간 SSH 제어**: 브라우저에서 원격 서버 터미널 조작
- **자동 서버 Health Check**: 30초마다 SSH 서버 상태 모니터링 및 실시간 알림
- **세션 기반 리소스 락**: 다단계 작업(SSH → SCP → SSH) 시 독점 사용 보장
- **SCP 파일 전송**: 서버 간 파일 전송 자동화
- **최적화된 출력 스트리밍**: Throttling 및 Carriage Return 처리로 클라이언트 부하 감소
- **포괄적인 에러 핸들링**: 5자리 에러 코드 시스템 및 구조화된 예외 처리

## 기술 스택

- **Framework**: FastAPI 0.104+
- **Python**: 3.11+
- **SSH**: Paramiko
- **WebSocket**: FastAPI WebSocket + Custom Connection Manager
- **Database**: SQLite (aiosqlite)
- **Logging**: Loguru

## 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd pp-backend-fastapi

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 설정

`.env` 파일을 프로젝트 루트에 생성:

```env
# 환경 설정
ENV=dev

# SSH 서버 인증 정보
HIWARE_ID=your_ssh_username
HIWARE_PW=your_ssh_password

# 서버 IP 주소
MDWAP1P_IP=xxx.xxx.xxx.xxx  # 개발/테스트 서버
MYPAP1D_IP=xxx.xxx.xxx.xxx  # 운영 서버
```

### 3. 실행

```bash
# 개발 모드 (자동 재시작)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

서버가 실행되면:
- Swagger 문서: http://localhost:8000/swagger/docs
- WebSocket 엔드포인트: ws://localhost:8000/ws/v1/stub

## API 엔드포인트

### WebSocket - STUB (대응답)

**연결**: `ws://localhost:8000/ws/v1/stub`

#### Welcome 메시지 (연결 시 자동 수신)

```json
{
  "type": "welcome",
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "lock_status": {
    "locked": false,
    "lock_owner": null
  },
  "session_status": {
    "active": false,
    "owner": null
  },
  "server_health": {
    "mdwap1p": {
      "server_name": "mdwap1p",
      "host": "10.10.10.1",
      "is_healthy": true,
      "last_checked": "2025-01-01T12:00:00",
      "consecutive_failures": 0,
      "consecutive_successes": 5
    },
    "mypap1d": {
      "server_name": "mypap1d",
      "host": "10.10.10.2",
      "is_healthy": true,
      "last_checked": "2025-01-01T12:00:00",
      "consecutive_failures": 0,
      "consecutive_successes": 5
    }
  }
}
```

#### 메시지 타입

##### 1. SSH 명령 실행

```json
// 전송
{
  "type": "ssh_command",
  "data": {
    "server_name": "mdwap1p",
    "command": "ls -la",
    "stop_phrase": "COMMAND_COMPLETE"
  }
}

// 수신 (실시간 출력)
{
  "type": "output",
  "data": "total 24\ndrwxr-xr-x  4 user group  128 Jan  1 12:00 .\n..."
}

// 수신 (완료)
{
  "type": "complete",
  "message": "Command execution completed"
}
```

##### 2. 세션 시작/종료 (다단계 작업용)

```json
// 세션 시작
{
  "type": "start_session"
}

// 수신
{
  "type": "session_started",
  "message": "Session started successfully",
  "session_owner": "550e8400-e29b-41d4-a716-446655440000"
}

// 세션 종료
{
  "type": "end_session"
}

// 수신
{
  "type": "session_ended",
  "message": "Session ended successfully"
}
```

##### 3. SCP 파일 전송

```json
// 전송 (세션 활성화 필요)
{
  "type": "scp_transfer",
  "data": {
    "transfer_name": "stub_data_transfer"
  }
}

// 수신 (진행 상황)
{
  "type": "output",
  "data": "Transferring files from mdwap1p to mypap1d..."
}

// 수신 (완료)
{
  "type": "complete",
  "message": "SCP transfer completed successfully"
}
```

##### 4. 서버 Health 상태 변경 (실시간 브로드캐스트)

```json
{
  "type": "server_health",
  "server_name": "mdwap1p",
  "is_healthy": false,
  "status": {
    "server_name": "mdwap1p",
    "host": "10.10.10.1",
    "is_healthy": false,
    "last_checked": "2025-01-01T12:00:30",
    "consecutive_failures": 2,
    "consecutive_successes": 0
  }
}
```

## 워크플로우 예제

### 단일 SSH 명령 실행

```javascript
// 1. WebSocket 연결
const ws = new WebSocket('ws://localhost:8000/ws/v1/stub');

// 2. Welcome 메시지 수신 (connection_id 저장)
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'welcome') {
    console.log('Connected with ID:', msg.connection_id);
  }
};

// 3. SSH 명령 전송
ws.send(JSON.stringify({
  type: 'ssh_command',
  data: {
    server_name: 'mdwap1p',
    command: 'ls -la',
    stop_phrase: 'COMMAND_COMPLETE'
  }
}));
```

### 다단계 작업 (SSH → SCP → SSH)

```javascript
// 1. 세션 시작
ws.send(JSON.stringify({ type: 'start_session' }));

// 2. 세션 시작 확인 후 첫 번째 SSH 작업
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.type === 'session_started') {
    // 첫 번째 SSH 작업: mdwap1p에서 데이터 준비
    ws.send(JSON.stringify({
      type: 'ssh_command',
      data: {
        server_name: 'mdwap1p',
        command: 'prepare_data.sh',
        stop_phrase: 'DATA_READY'
      }
    }));
  }

  if (msg.type === 'complete' && msg.message.includes('prepare_data')) {
    // 두 번째 작업: SCP 전송
    ws.send(JSON.stringify({
      type: 'scp_transfer',
      data: { transfer_name: 'stub_data_transfer' }
    }));
  }

  if (msg.type === 'complete' && msg.message.includes('SCP')) {
    // 세 번째 SSH 작업: mypap1d에서 데이터 처리
    ws.send(JSON.stringify({
      type: 'ssh_command',
      data: {
        server_name: 'mypap1d',
        command: 'process_data.sh',
        stop_phrase: 'PROCESS_COMPLETE'
      }
    }));
  }

  if (msg.type === 'complete' && msg.message.includes('process_data')) {
    // 모든 작업 완료, 세션 종료
    ws.send(JSON.stringify({ type: 'end_session' }));
  }
};
```

## 에러 처리

### 에러 코드 체계

- **1XXX**: 일반 에러 (인증, 검증 등)
- **2XXX**: SSH 에러
  - 20XXX: 연결 에러
  - 21XXX: 인증 에러
  - 22XXX: 명령 실행 에러
  - 24XXX: SCP 전송 에러
  - 25XXX: Health Check 에러
- **3XXX**: WebSocket 에러
- **5XXX**: 비즈니스 로직 에러
  - 50004: 세션 이미 활성화됨
  - 50005: 활성 세션 없음
  - 50006: 세션 권한 없음
  - 50008: 리소스 잠금됨

### 에러 응답 예제

```json
{
  "type": "error",
  "message": "Session already active",
  "detail": "Session is already active (owner: other-connection-id)",
  "error_code": 50004
}
```

## 프로젝트 구조

```
pp-backend-fastapi/
├── app/
│   ├── main.py                      # FastAPI 앱 엔트리 포인트
│   ├── api/                         # API 라우터
│   │   └── v1/
│   │       ├── router.py            # API 라우팅 설정
│   │       └── websockets/
│   │           └── stub.py          # STUB WebSocket 컨트롤러
│   ├── core/                        # 핵심 설정
│   │   ├── config.py                # 환경 설정
│   │   ├── logger.py                # 로깅 설정
│   │   └── exceptions/              # 예외 처리 시스템
│   │       ├── base.py              # 예외 클래스
│   │       ├── error_codes.py       # 에러 코드 정의
│   │       ├── handlers.py          # FastAPI 예외 핸들러
│   │       └── websocket.py         # WebSocket 예외 핸들러
│   ├── domains/                     # 도메인 비즈니스 로직
│   │   └── stub/
│   │       └── services/
│   │           ├── stub_ssh_service.py      # SSH 서비스
│   │           └── health_check_service.py  # Health Check 서비스
│   └── infrastructures/             # 인프라 레이어
│       ├── ssh/                     # SSH 인프라
│       │   ├── base.py              # BaseSSHService
│       │   └── config.py            # SSH 설정 관리
│       └── websocketV2/             # WebSocket 인프라
│           ├── connection_manager.py # 연결 관리
│           └── event_handler.py      # 이벤트 핸들러
├── test/                            # 테스트
├── .env                             # 환경 변수 (git ignore)
├── requirements.txt                 # Python 의존성
├── CLAUDE.md                        # Claude Code 가이드
└── README.md                        # 프로젝트 문서
```

## 개발 가이드

### 새로운 SSH 서비스 추가하기

1. `BaseSSHService`를 상속받는 서비스 클래스 생성:

```python
# app/domains/your_domain/services/your_ssh_service.py
from app.infrastructures.ssh import BaseSSHService

class YourSSHService(BaseSSHService):
    async def your_custom_method(self):
        # BaseSSHService의 메서드 사용
        await self.connect(host, username, password)
        stdout, stderr, exit_code = await self.execute_command("your command")
        await self.disconnect()
```

2. SSH 서버 설정 추가:

```python
# app/infrastructures/ssh/config.py
_SSH_SERVERS = {
    "your_server": SSHConfig(
        name="your_server",
        host=os.getenv("YOUR_SERVER_IP"),
        username=os.getenv("SSH_USERNAME"),
        password=os.getenv("SSH_PASSWORD"),
    )
}
```

### WebSocket 핸들러 추가하기

```python
# app/api/v1/websockets/your_controller.py
from app.infrastructures.websocketV2 import WebSocketHandler

ws_handler = WebSocketHandler(ws_manager)

@ws_handler.on_message("your_message_type")
async def handle_your_message(connection_id: str, data: dict):
    # 메시지 처리 로직
    await ws_manager.send_json(connection_id, {
        "type": "response",
        "data": "your response"
    })
```

### 새로운 예외 추가하기

1. 에러 코드 정의:

```python
# app/core/exceptions/error_codes.py
YOUR_ERROR = (60000, "Your error message", 400)
```

2. 예외 클래스 생성:

```python
# app/core/exceptions/base.py
class YourException(BaseAppException):
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(ErrorCode.YOUR_ERROR, detail=detail, **kwargs)
```

## 테스트

```bash
# 전체 테스트 실행
python -m pytest test/

# 특정 테스트 실행
python test/ssh_test.py
python test/test_stub_websocket.py

# 커버리지 확인
pytest --cov=app test/
```

## 라이선스

이 프로젝트는 비공개 프로젝트입니다.

## 기여

내부 개발팀 전용 프로젝트입니다.

## 문의

프로젝트 관련 문의사항은 개발팀에 문의해주세요.

---

**Note**: 이 문서는 프로젝트의 현재 상태를 반영합니다. 새로운 기능이 추가되거나 변경사항이 있을 경우 업데이트됩니다.
