# SSH Service 사용 가이드

## 개요

SSH Infrastructure는 모든 도메인이 공통으로 사용할 수 있는 SSH 연결 및 인증 기능을 제공합니다.

## 구조

```
app/infrastructures/ssh/
├── base.py              # BaseSSHService (공통 기능)
├── config.py            # SSHConfigManager (서버 설정)
└── __init__.py          # Export

app/domains/
├── stub/services/
│   └── stub_ssh_service.py    # 인터랙티브 셸 (StubSSHService)
├── bmx4/services/
│   └── bmx4_ssh_service.py    # 배치 명령 실행 (Bmx4SSHService)
└── bmx5/services/
    └── bmx5_ssh_service.py    # SFTP 파일 전송 (Bmx5SSHService)
```

---

## 기본 사용법

### 1. 서버 설정 관리

```python
from app.infrastructures.ssh import get_ssh_config, SSHConfigManager

# 설정된 서버 조회
config = get_ssh_config("mdwap1p")
print(f"Host: {config.host}, User: {config.username}")

# 모든 서버 목록
servers = SSHConfigManager.list_servers()
for name, config in servers.items():
    print(f"{name}: {config.host}")

# 런타임에 서버 추가 (테스트용)
SSHConfigManager.add_server(
    name="test_server",
    host="192.168.1.100",
    username="testuser",
    password="testpass"
)
```

### 2. BaseSSHService 직접 사용

간단한 명령 실행만 필요한 경우:

```python
from app.infrastructures.ssh import BaseSSHService, get_ssh_config

# 서버 설정 로드
config = get_ssh_config("mdwap1p")

# SSH 연결
ssh = BaseSSHService()
await ssh.connect(
    host=config.host,
    username=config.username,
    password=config.password
)

# 명령 실행
stdout, stderr, exit_code = await ssh.execute_command("ls -la")
print(f"Output: {stdout}")
print(f"Exit code: {exit_code}")

# 연결 해제
await ssh.disconnect()
```

### 3. 커스텀 SSH 서비스 만들기

도메인별 특화 기능이 필요한 경우 BaseSSHService를 상속:

```python
from app.infrastructures.ssh import BaseSSHService, get_ssh_config
from app.core.exceptions import SSHCommandException

class MyDomainSSHService(BaseSSHService):
    """내 도메인 전용 SSH 서비스"""

    async def connect_to_server(self, server_name: str) -> bool:
        """편의 메서드: 서버 이름으로 연결"""
        config = get_ssh_config(server_name)
        return await self.connect(
            config.host,
            config.username,
            config.password,
            config.port
        )

    async def my_custom_operation(self, param: str):
        """도메인 전용 작업"""
        if not self.is_connected:
            raise SSHCommandException(detail="Not connected")

        # 부모 클래스의 메서드 활용
        stdout, stderr, exit_code = await self.execute_command(
            f"my_command {param}"
        )

        # 결과 처리
        return {"output": stdout, "success": exit_code == 0}

# 사용
service = MyDomainSSHService()
await service.connect_to_server("mdwap1p")
result = await service.my_custom_operation("test")
await service.disconnect()
```

---

## 도메인별 SSH 서비스

### STUB: 인터랙티브 셸 (StubSSHService)

실시간 출력 스트리밍이 필요한 경우:

```python
from app.domains.stub.services.stub_ssh_service import StubSSHService

# 서비스 생성
ssh = StubSSHService()

# 출력 콜백 설정
async def output_handler(text: str):
    print(f"[OUTPUT] {text}", end='')

ssh.set_output_callback(output_handler)

# 서버 연결
await ssh.connect_to_server("mdwap1p")

# 인터랙티브 셸 실행
await ssh.start_interactive_shell(
    command="my_interactive_command",
    stop_phrase="PROMPT>",  # 이 문구가 나오면 자동 종료
    recv_timeout=0.1
)

# 연결 해제
await ssh.disconnect()
```

**주요 기능:**
- PTY 기반 인터랙티브 셸
- 실시간 출력 스트리밍
- Stop phrase 자동 감지
- WebSocket을 통한 실시간 전송에 최적화

### BMX4: 배치 명령 실행 (Bmx4SSHService)

여러 명령을 순차 실행하고 결과를 집계:

```python
from app.domains.bmx4.services.bmx4_ssh_service import Bmx4SSHService

# 서비스 생성
ssh = Bmx4SSHService()
await ssh.connect_to_server("mdwap1p")

# 배치 명령 실행
commands = [
    "cd /app",
    "ls -la",
    "cat config.txt",
    "pwd"
]

summary = await ssh.execute_batch_commands(
    commands=commands,
    stop_on_error=True,  # 에러 발생 시 중단
    command_timeout=30.0
)

print(f"Total: {summary['total_commands']}")
print(f"Success: {summary['success']}")
print(f"Failed: {summary['failed']}")

for result in summary['results']:
    print(f"Command {result['index']}: {result['command']}")
    print(f"  Exit code: {result['exit_code']}")
    print(f"  Output: {result['stdout'][:100]}...")

# 재시도 로직이 필요한 경우
stdout, stderr, exit_code = await ssh.execute_command_with_retry(
    command="flaky_command",
    max_retries=3,
    retry_delay=2.0
)

await ssh.disconnect()
```

**주요 기능:**
- 배치 명령 순차 실행
- 결과 집계 및 통계
- 재시도 로직 내장
- Stop-on-error 옵션

### BMX5: SFTP 파일 전송 (Bmx5SSHService)

파일 업로드/다운로드 및 원격 스크립트 실행:

```python
from app.domains.bmx5.services.bmx5_ssh_service import Bmx5SSHService

# 서비스 생성
ssh = Bmx5SSHService()
await ssh.connect_to_server("mdwap1p")

# SFTP 세션 열기
await ssh.open_sftp()

# 파일 업로드
await ssh.upload_file(
    local_path="/local/path/file.txt",
    remote_path="/remote/path/file.txt",
    create_dirs=True  # 원격 디렉토리 자동 생성
)

# 파일 다운로드
await ssh.download_file(
    remote_path="/remote/log.txt",
    local_path="/local/log.txt"
)

# 스크립트 업로드 및 실행
stdout, stderr, exit_code = await ssh.upload_and_execute_script(
    local_script_path="/local/scripts/process.sh",
    remote_script_path="/tmp/process.sh",
    script_args=["arg1", "arg2"],
    cleanup=True  # 실행 후 스크립트 삭제
)

print(f"Script output: {stdout}")

# 원격 파일 목록
files = await ssh.list_remote_files("/remote/dir")
for file in files:
    print(f"  - {file}")

# SFTP 세션 닫기
await ssh.close_sftp()
await ssh.disconnect()
```

**주요 기능:**
- SFTP 파일 업로드/다운로드
- 원격 디렉토리 자동 생성
- 스크립트 전송 및 실행
- 원격 파일 관리

---

## 에러 처리

모든 SSH 작업은 적절한 예외를 발생시킵니다:

```python
from app.core.exceptions import (
    SSHConnectionException,
    SSHAuthException,
    SSHCommandException
)

try:
    await ssh.connect(host, username, password)
except SSHConnectionException as e:
    print(f"Connection error: {e.code} - {e.detail}")
except SSHAuthException as e:
    print(f"Authentication failed: {e.detail}")

try:
    stdout, stderr, exit_code = await ssh.execute_command("some_command")
except SSHCommandException as e:
    print(f"Command failed: {e.code} - {e.detail}")
```

**에러 코드:**
- `20000-20999`: SSH 연결 에러
- `21000-21999`: SSH 인증 에러
- `22000-22999`: SSH 명령 실행 에러

자세한 내용은 `docs/ERROR_HANDLING_GUIDE.md` 참조.

---

## 베스트 프랙티스

### 1. 항상 연결 해제

```python
ssh = StubSSHService()
try:
    await ssh.connect_to_server("mdwap1p")
    # 작업 수행
finally:
    await ssh.disconnect()  # 항상 실행
```

### 2. Context Manager 사용 (권장)

```python
# TODO: AsyncContextManager 구현 예정
async with StubSSHService() as ssh:
    await ssh.connect_to_server("mdwap1p")
    # 작업 수행
    # 자동으로 disconnect 호출됨
```

### 3. 타임아웃 설정

```python
# 연결 타임아웃
await ssh.connect(host, username, password, timeout=10.0)

# 명령 타임아웃
stdout, stderr, exit_code = await ssh.execute_command(
    "long_running_command",
    timeout=60.0
)
```

### 4. 로깅 활용

모든 SSH 작업은 자동으로 로깅됩니다:

```python
# 로그 레벨 설정
import logging
logging.getLogger("app.infrastructures.ssh").setLevel(logging.DEBUG)
```

### 5. 연결 정보 확인

```python
info = ssh.get_connection_info()
print(f"Connected: {info['is_connected']}")
print(f"Host: {info['host']}")
print(f"Transport active: {info['transport_active']}")
```

---

## 마이그레이션 가이드

### 기존 코드를 새 구조로 변경

**Before:**
```python
# 각 서비스마다 연결 로직 중복
class MyService:
    async def connect(self, host, user, password):
        # Paramiko 연결 로직 반복...
        self.transport = paramiko.Transport(...)
        self.transport.auth_password(...)
```

**After:**
```python
from app.infrastructures.ssh import BaseSSHService

class MyService(BaseSSHService):
    # 연결 로직 상속받음, 도메인 로직만 구현
    async def my_domain_operation(self):
        # self.transport, self.ssh_client 등 사용 가능
        pass
```

---

## FAQ

**Q: BaseSSHService를 직접 사용해야 하나요?**
A: 간단한 명령 실행만 필요하면 직접 사용 가능합니다. 하지만 대부분은 도메인별 SSH 서비스를 만들어 사용하는 것이 좋습니다.

**Q: 여러 서버에 동시 연결이 가능한가요?**
A: 네, 각각 별도의 서비스 인스턴스를 만들면 됩니다.

```python
ssh1 = StubSSHService()
ssh2 = StubSSHService()
await ssh1.connect_to_server("mdwap1p")
await ssh2.connect_to_server("mypap1d")
```

**Q: 연결 풀링을 지원하나요?**
A: 현재는 지원하지 않습니다. 필요하면 도메인 서비스에서 직접 구현하거나, dependency injection을 통해 싱글톤으로 관리할 수 있습니다.

**Q: SSH 키 인증을 지원하나요?**
A: 현재는 비밀번호 인증만 지원합니다. SSH 키 인증이 필요하면 `BaseSSHService._authenticate()` 메서드를 오버라이드하여 구현할 수 있습니다.

**Q: 새로운 서버를 추가하려면?**
A: `.env` 파일에 환경 변수를 추가하고, `ssh/config.py`의 `SSHConfigManager._initialize()`에 서버 설정을 추가하세요.

---

## 추가 참고 자료

- [ERROR_HANDLING_GUIDE.md](./ERROR_HANDLING_GUIDE.md) - 에러 처리 상세 가이드
- [CLAUDE.md](../CLAUDE.md) - 전체 프로젝트 구조
- Paramiko 공식 문서: https://docs.paramiko.org/
