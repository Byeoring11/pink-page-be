# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based backend service for "Pink-Page" that provides SSH connectivity and WebSocket-based real-time communication features. The application connects to remote HIWARE servers via SSH and provides WebSocket APIs for interactive terminal sessions with real-time output streaming.

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
- WDEXGM1P_IP, EDWAP1T_IP, MYPAP1D_IP: Server IPs for each environment

## Architecture

### Core Structure
- **Entry Point**: `app/main.py` - FastAPI app creation with middleware and router setup
- **Configuration**: `app/core/config.py` - Environment-based settings via Pydantic
- **Database**: SQLite with async support (aiosqlite)
- **Logging**: `app/core/logger.py` - Structured logging across the application

### Domain-Driven Design
The codebase follows a layered architecture with clear separation of concerns:

**Domains** (`app/domains/`):
- Business logic organized by domain (e.g., `deud/`, `stub/`)
- Services coordinate between infrastructure and API layers
- Schemas define domain-specific data structures

**Infrastructure** (`app/infrastructures/`):
- External system integrations (SSH, WebSocket)
- Reusable components independent of business logic
- Two WebSocket implementations exist: `websocket/` (legacy) and `websocketV2/` (new decorator-based)

**API Layer** (`app/api/v1/`):
- REST endpoints: `/api/v1/` prefix
- WebSocket endpoints: `/ws/v1/` prefix
- Routers delegate to domain services via dependency injection

### WebSocket Architecture

#### Legacy WebSocket (`app/infrastructures/websocket/`)
Used by the `deud` domain with dependency injection pattern:
- `WebSocketService`: Connection lifecycle and message routing
- `TaskCoordinator`: Orchestrates task execution and state management
- Message-based action routing (START_TASK, CANCEL_TASK, GET_STATUS)

#### New WebSocket (`app/infrastructures/websocketV2/`)
Used by the `stub` domain with decorator-based event handlers:
- `WebSocketManager`: Low-level connection management with send/receive methods
- `WebSocketHandler`: Event-based architecture with `@on_message()` and `@on_connect()` decorators
- Controllers register handlers for specific message types (e.g., `ssh_command`, `ssh_input`)

Example pattern:
```python
ws_manager = WebSocketManager()
ws_handler = WebSocketHandler(ws_manager)

@ws_handler.on_message("ssh_command")
async def handle_command(connection_id: str, data: dict):
    # Handle message type
```

### SSH Connection Patterns

#### Interactive Shell with Real-time Streaming (`StubSSHService`)
Located in `app/domains/stub/services/stub_ssh_service.py`:
- Direct Paramiko Transport API usage for low-level control
- Two-phase authentication: `auth_none()` fallback to `auth_password()`
- PTY-based interactive shell with real-time output streaming via callbacks
- Non-blocking receive with `select.select()` for async compatibility
- Stop phrase detection for automated command completion
- Pattern: Connect → Open PTY → Execute command → Stream output → Detect stop phrase → Exit

#### Standard SSH Operations (`DeudService` pattern)
- Higher-level SSH operations via service layer
- Task coordination for batch operations
- State management for long-running SSH tasks

### API Routing

**WebSocket Endpoints** (`app/api/v1/router.py`):
- `/ws/v1/deud` - Legacy WebSocket with dependency injection (uses `TaskCoordinator`)
- `/ws/v1/stub/{connection_id}` - New WebSocket with event handlers (uses `StubWebSocketController`)

**Swagger Documentation**:
- Available at `/swagger/docs` (root `/` redirects here)

### Target Servers
The application connects to three HIWARE server environments:
- `wdexgm1p`: Development server
- `edwap1t`: Test environment
- `mypap1d`: Production server

Server configurations are retrieved via `get_server_config()` methods in SSH services.

### Dependency Injection
Located in `app/api/dependencies.py`:
- Provides service instances to API endpoints via FastAPI's `Depends()`
- Manages singleton instances and lifecycle
- Used primarily with the legacy WebSocket architecture

### Key Implementation Notes

1. **Async SSH**: The `StubSSHService` bridges synchronous Paramiko with async FastAPI using `asyncio.sleep()` and non-blocking I/O patterns
2. **Output Callbacks**: SSH services use callback functions to stream output in real-time to WebSocket clients
3. **Stop Phrase Detection**: Commands complete automatically when a specific prompt pattern is detected in output (e.g., "CICS_PROMPT>")
4. **Connection ID Pattern**: New WebSocket implementation uses explicit connection IDs in the URL path for multiplexing