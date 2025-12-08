# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based backend service for "Pink-Page" that provides SSH connectivity and WebSocket-based real-time communication features. The application connects to remote HIWARE servers via SSH and provides WebSocket APIs for interactive terminal sessions with real-time output streaming.

Key features include:
- Server-generated WebSocket connection IDs
- Session-based resource locking for multi-step workflows
- Real-time SSH server health monitoring
- Optimized shell output streaming with throttling
- SCP file transfer between remote servers
- Comprehensive exception handling system

## Development Commands

### Running the Application
```bash
# Development with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
python -m pytest test/

# Run specific test file
python test/ssh_test.py
python test/test_stub_websocket.py
```

### Environment Setup
Required environment variables in `.env`:
- ENV: Environment name (dev/prod)
- HIWARE_ID, HIWARE_PW: SSH credentials for HIWARE servers
- MDWAP1P_IP, MYPAP1D_IP: Server IPs for each environment

## Architecture

### Core Structure
- **Entry Point**: `app/main.py` - FastAPI app creation with middleware, router setup, and lifespan events
- **Configuration**: `app/core/config.py` - Environment-based settings via Pydantic
- **Database**: SQLite with async support (aiosqlite)
- **Logging**: `app/core/logger.py` - Structured logging across the application

### Domain-Driven Design
The codebase follows a layered architecture with clear separation of concerns:

**Domains** (`app/domains/`):
- Business logic organized by domain: `stub/`, `bmx4/`, `bmx5/`, `diff/`
- Services coordinate between infrastructure and API layers
- Schemas define domain-specific data structures
- **Health Check Service**: Background SSH server monitoring (stub domain)

**Infrastructure** (`app/infrastructures/`):
- External system integrations (SSH, WebSocket)
- Reusable components independent of business logic
- **SSH Module** (`ssh/`): Base SSH service with connection, authentication, command execution, and health checks
- **WebSocket Module** (`websocketV2/`): Decorator-based event handlers for real-time communication

**API Layer** (`app/api/v1/`):
- REST endpoints: `/api/v1/` prefix
- WebSocket endpoints: `/ws/v1/` prefix
- Routers delegate to domain services via dependency injection

**Exception Handling** (`app/core/exceptions/`):
- Structured error code system (5-digit codes by category)
- Custom exception classes with hierarchy
- Global exception handlers for REST API and WebSocket
- Error codes: 1XXX (General), 2XXX (SSH), 3XXX (WebSocket), 4XXX (DB), 5XXX (Business)

### WebSocket Architecture

**WebSocketV2** (`app/infrastructures/websocketV2/`):
- `WebSocketManager`: Low-level connection management with send/receive methods
- `WebSocketHandler`: Event-based architecture with `@on_message()` and `@on_connect()` decorators
- Controllers register handlers for specific message types (e.g., `ssh_command`, `ssh_input`, `start_session`)
- Used by all domains (stub, bmx4, bmx5, diff)
- Broadcast support with exception handling

Example pattern:
```python
ws_manager = WebSocketManager()
ws_handler = WebSocketHandler(ws_manager)

@ws_handler.on_message("ssh_command")
async def handle_command(connection_id: str, data: dict):
    # Handle message type
```

**Connection ID Management**:
- Server-side UUID generation on connection
- Connection ID sent to client in welcome message
- No client-side ID generation required

**Exception Handling in WebSocket**:
- Use `WebSocketErrorHandler` for manual error handling
- Use `@handle_ws_errors` decorator for automatic error handling
- Errors are sent to client as JSON with error code and message
- See `app/core/exceptions/websocket.py` for implementation

### SSH Infrastructure (`app/infrastructures/ssh/`)

**Base SSH Service** (`base.py`):
- Common SSH connection and authentication logic
- Two-phase authentication: `auth_none()` fallback to `auth_password()`
- Basic command execution with timeout support
- Static `health_check()` method for TCP connectivity testing
- Automatic exception handling with custom SSH exceptions
- All domain SSH services inherit from `BaseSSHService`

**SSH Configuration** (`config.py`):
- Centralized server configuration management via `SSHConfigManager`
- Server configs loaded from environment variables
- SCP transfer configurations with `SCPTransferConfig`
- Convenience functions: `get_ssh_config(server_name)`, `get_scp_config(transfer_name)`

**Usage Pattern**:
```python
from app.infrastructures.ssh import BaseSSHService, get_ssh_config

class MySSHService(BaseSSHService):
    async def my_custom_operation(self):
        # Use inherited connect(), execute_command(), disconnect()
        pass

# Connect to server
config = get_ssh_config("mdwap1p")
service = MySSHService()
await service.connect(config.host, config.username, config.password)
```

### Domain-Specific SSH Services

**STUB** (`stub_ssh_service.py`):
- Extends `BaseSSHService` for interactive shell operations
- PTY-based shell with real-time output streaming via callbacks
- **Throttling**: Configurable output buffering to reduce client load (default: 0.1s)
- **Carriage Return Handling**: Detects progress bar updates (`\r`) to avoid output flooding
- Stop phrase detection for automated command completion
- **SCP Transfer**: Server-to-server file transfer using sshpass and config-based parameters
- Pattern: Connect → Open PTY → Execute → Stream output → Detect stop → Exit

**BMX4** (`bmx4_ssh_service.py`):
- Extends `BaseSSHService` for batch command execution
- Sequential command execution with result aggregation
- Retry logic with configurable attempts and delays
- Stop-on-error support for batch operations

**BMX5** (`bmx5_ssh_service.py`):
- Extends `BaseSSHService` for SFTP operations
- File upload/download functionality
- Script transfer and remote execution
- Remote file management (list, create directories)

**Health Check Service** (`health_check_service.py`):
- Background service monitoring SSH server availability
- Runs every 30 seconds (configurable)
- Tracks server status with consecutive failure/success counts
- Callback mechanism for status change notifications
- Real-time broadcast to all WebSocket clients
- Managed by FastAPI lifespan events

**Error Handling**:
- All SSH operations raise exceptions from `app.core.exceptions`
- `SSHConnectionException` for connection errors
- `SSHAuthException` for authentication errors
- `SSHCommandException` for command execution errors
- `SSHSCPException` for file transfer errors
- `SSHHealthCheckException` and `SSHHealthCheckServiceException` for health check errors
- Exceptions are automatically logged and converted to HTTP/WebSocket responses

### Resource Locking System

**Session Lock** (STUB domain):
- Multi-step workflow protection
- Reserves SSH service for sequence of operations (e.g., SSH → SCP → SSH)
- Explicit start/end via WebSocket messages (`start_session`, `end_session`)
- Only session owner can perform operations while active
- Ensures sequential execution of the 3-step workflow as one atomic unit

**asyncio Task Management** (NEW):
- All SSH operations run as managed asyncio Tasks
- Controller maintains `ssh_tasks` dictionary: `connection_id -> asyncio.Task`
- Tasks can be cancelled immediately via `task.cancel()`
- Graceful cancellation with `asyncio.CancelledError` handling
- Immediate termination on user stop or disconnect
- No polling or flag checking required - native Python async cancellation
- Comprehensive exception handling for Task lifecycle:
  - `StubTaskAlreadyRunningException` (50010): Prevents duplicate tasks for same connection
  - `StubTaskNotFoundException` (50011): Handles attempts to cancel non-existent tasks
  - `StubTaskCancellationTimeoutException` (50012): 5-second timeout for task cancellation
  - `StubTaskCancellationFailedException` (50013): Unexpected cancellation failures
  - `StubTaskCleanupFailedException` (50014): SSH service cleanup errors

**WebSocket Message Types**:
- `start_session`: Acquire session lock for multi-step workflow
- `end_session`: Release session lock and cancel all active tasks
- `ssh_command`: Execute interactive shell command (requires session lock, runs as Task)
- `scp_transfer`: Transfer files between servers (requires session lock)

### API Routing

**WebSocket Endpoints** (`app/api/v1/router.py`):
- `/ws/v1/stub` - STUB WebSocket with server-generated connection IDs
- Additional domain-specific WebSocket endpoints for bmx4, bmx5, diff

**Welcome Message** (sent on connection):
```json
{
  "type": "welcome",
  "message": "Connected to Stub SSH WebSocket",
  "connection_id": "uuid-generated-id",
  "session_status": {
    "active": false,
    "owner": null
  },
  "server_health": {
    "mdwap1p": {
      "server_name": "mdwap1p",
      "host": "xxx.xxx.xxx.xxx",
      "is_healthy": true,
      "last_checked": "2025-01-01T12:00:00",
      "consecutive_failures": 0,
      "consecutive_successes": 5
    }
  }
}
```

**Real-time Health Updates**:
```json
{
  "type": "server_health",
  "server_name": "mdwap1p",
  "is_healthy": false,
  "status": { ... }
}
```

**Swagger Documentation**:
- Available at `/swagger/docs` (root `/` redirects here)

**Error Responses**:
- All endpoints return standardized error responses with error codes
- REST API: `{"success": false, "error": {"code": 20000, "message": "...", "detail": "..."}}`
- WebSocket: `{"type": "error", "success": false, "error": {"code": 20000, "message": "..."}}`

### Exception System

**Error Code Ranges**:
- **1XXX**: General errors (validation, auth, resources)
- **2XXX**: SSH errors
  - 20XXX: Connection errors
  - 21XXX: Authentication errors
  - 22XXX: Command execution errors
  - 23XXX: Configuration errors
  - 24XXX: SCP transfer errors
  - 25XXX: Health check errors
- **3XXX**: WebSocket errors
  - 30XXX: Connection errors
  - 31XXX: Message errors
  - 32XXX: Handler errors
  - 33XXX: Broadcast errors
- **4XXX**: Database errors
- **5XXX**: Business logic errors
  - 50XXX: STUB domain (sessions, locks, transfers, tasks)
    - 50004-50007: Session management
    - 50008: Resource locking
    - 50009: File transfers
    - 50010-50014: Task management
  - 51XXX: BMX4 domain
  - 52XXX: BMX5 domain
  - 53XXX: DIFF domain

**Exception Classes**:
- All exceptions inherit from `BaseAppException`
- Category-based hierarchy: `SSHException`, `WebSocketException`, `BusinessException`
- Context-aware error details and original exception tracking
- Automatic HTTP status code mapping

### Target Servers
The application connects to HIWARE server environments:
- `mdwap1p`: Development/Test server
- `mypap1d`: Production server

Server configurations are managed centrally via `SSHConfigManager` in `app/infrastructures/ssh/config.py`.
Environment variables required: `MDWAP1P_IP`, `MYPAP1D_IP`, `HIWARE_ID`, `HIWARE_PW`.

### SCP Transfer Configuration

SCP transfers are configured in `app/infrastructures/ssh/config.py`:
```python
_SCP_TRANSFERS = {
    "stub_data_transfer": SCPTransferConfig(
        name="stub_data_transfer",
        src_server="mdwap1p",
        src_path="/nbsftp/myd/myp/snd/postgresql_unload/*.dat",
        dst_server="mypap1d",
        dst_path="/shbftp/myd/myp/rcv/mock/",
    )
}
```

Usage in service layer:
```python
await ssh_service.scp_transfer(
    transfer_name="stub_data_transfer",
    output_callback=my_callback
)
```

### Application Lifecycle

**Lifespan Events** (`app/main.py`):
- **Startup**: Health check service starts background monitoring
- **Shutdown**: Graceful health check service termination
- Service failures don't prevent application startup (optional feature)

### Key Implementation Notes

1. **SSH Infrastructure Pattern**: All SSH operations inherit from `BaseSSHService` to avoid code duplication
   - Common logic (connection, authentication) in base class
   - Domain-specific logic (interactive shell, batch, SFTP, SCP) in derived classes
   - Centralized configuration via `SSHConfigManager`

2. **Async SSH Bridge**: SSH services bridge synchronous Paramiko with async FastAPI
   - Use `asyncio.sleep(0)` to yield to event loop
   - Non-blocking I/O with `select.select()` for real-time streaming
   - Proper exception handling with custom SSH exceptions

3. **Output Optimization**:
   - Throttling prevents client overload during high-frequency output
   - Carriage return detection handles progress bars correctly
   - Configurable buffer intervals (default: 0.1s)

4. **Domain Specialization**:
   - **STUB**: Interactive PTY shells with output callbacks, stop phrase detection, SCP transfers
   - **BMX4**: Batch command execution with retry logic and result aggregation
   - **BMX5**: SFTP file operations and remote script execution

5. **Connection Management**:
   - Server-side UUID generation for all WebSocket connections
   - No client-side ID management required
   - Connection ID included in welcome message

6. **Resource Protection**:
   - Session lock for multi-step workflows
   - Only session owner can perform operations during active session
   - Session status broadcast to all clients in real-time

7. **Health Monitoring**:
   - Background service checks all configured servers every 30 seconds
   - TCP socket connectivity test (port 22)
   - Consecutive failure tracking (2 failures = unhealthy)
   - Real-time status broadcast to all connected clients
   - Initial status in welcome message

8. **Error Resilience**:
   - Health check failures don't crash the application
   - Callback errors don't stop monitoring
   - Broadcast failures are isolated and logged
   - All exceptions include context and original error tracking

9. **Task-Based Operation Control** (NEW):
   - SSH operations executed as asyncio Tasks for cancellability
   - `_execute_ssh_command()` contains actual SSH logic
   - `handle_ssh_command()` creates and registers Task
   - Tasks cancelled on `end_session` or disconnect
   - `CancelledError` caught in both controller and SSH service
   - Pattern: Create Task → Register → Execute → Cancel on demand → Cleanup
   - Ensures immediate response to user stop actions without race conditions
   - **Exception Safety**:
     - Duplicate task prevention with `StubTaskAlreadyRunningException`
     - 5-second cancellation timeout with `asyncio.wait_for()`
     - Timeout errors handled via `StubTaskCancellationTimeoutException`
     - Cancellation failures caught as `StubTaskCancellationFailedException`
     - Cleanup errors isolated with `StubTaskCleanupFailedException`
     - All errors logged with full context and sent to client via WebSocket
     - Graceful degradation on disconnect (errors logged but not sent)
