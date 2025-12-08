# Work History System - Deployment Guide

## Overview

The Work History System is a complete solution for tracking Stub workflow executions. It automatically records every data loading operation, storing one database record per customer number.

### Key Features
- **Automatic Recording**: History is saved automatically after successful workflow completion
- **Granular Tracking**: One row per customer number (10 customers = 10 rows)
- **Rich Metadata**: Tracks client IP, execution time, timestamps, WebSocket connection ID
- **Query API**: RESTful endpoints for listing, filtering, and analyzing history
- **Production Ready**: Auto-initialization, error handling, and cleanup capabilities

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (SvelteKit)                                        │
│  - Generates batch_id (UUID) at workflow start              │
│  - Records start/completion timestamps                       │
│  - Calls POST /api/v1/stub/load-history on success         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                           │
│  - REST API Router (app/api/v1/routers/stub.py)            │
│  - Service Layer (StubLoadHistoryService)                   │
│  - Pydantic Schemas (validation & serialization)            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Database (SQLite)                                           │
│  - File: data/stub_history.db                               │
│  - Table: stub_load_history                                 │
│  - Indexes: batch_id, customer_number, client_ip, dates     │
└─────────────────────────────────────────────────────────────┘
```

## Files Created

### Backend Files

1. **Migration SQL** (`migrations/create_stub_load_history.sql`)
   - Table creation with all fields and constraints
   - Index creation for performance
   - Example queries for reference

2. **Schemas** (`app/domains/stub/schemas/stub_load_history_schemas.py`)
   - `StubLoadHistoryCreate`: Request validation
   - `StubLoadHistoryResponse`: Single record response
   - `StubLoadHistoryListResponse`: Paginated list response
   - `StubLoadHistorySummary`: Batch aggregation response

3. **Service** (`app/domains/stub/services/stub_load_history_service.py`)
   - `initialize_db()`: Creates table and indexes
   - `create_history()`: Inserts records per customer number
   - `get_history_list()`: Query with filters and pagination
   - `get_batch_summary()`: Aggregate batch statistics
   - `get_customer_history()`: Customer-specific queries
   - `delete_old_records()`: Cleanup old data

4. **REST API Router** (`app/api/v1/routers/stub.py`)
   - POST `/api/v1/stub/load-history`: Create history
   - GET `/api/v1/stub/load-history`: List with filters
   - GET `/api/v1/stub/load-history/batch/{batch_id}`: Batch summary
   - GET `/api/v1/stub/load-history/customer/{customer_number}`: Customer history
   - DELETE `/api/v1/stub/load-history/cleanup`: Delete old records

### Frontend Files

1. **API Client** (`pp-frontend/src/lib/api/stubApi.ts`)
   - TypeScript interfaces for all request/response types
   - API functions for all endpoints
   - Type-safe client implementation

2. **WebSocket Service** (`pp-frontend/src/routes/stub/websocket.ts`)
   - Added `recordWorkflowHistory()` method
   - Automatic history recording after step 3 completion
   - Batch ID generation and timing tracking

## Deployment Steps

### 1. Backend Setup

The backend is already configured and will auto-initialize. No manual steps required.

**What happens automatically:**
- On application startup, `main.py` calls `StubLoadHistoryService.initialize_db()`
- Database file is created at `data/stub_history.db` if it doesn't exist
- Table and indexes are created
- Router is registered at `/api/v1/stub/*`

**Verify deployment:**
```bash
# Start the backend
cd pp-backend-fastapi
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Check logs for:
# "Stub Load History 데이터베이스 초기화 완료"

# Verify endpoints in Swagger:
# http://localhost:8000/swagger/docs
# Look for "Stub-REST" tag with 5 endpoints
```

### 2. Frontend Setup

The frontend integration is already complete. No additional steps required.

**What happens automatically:**
- When workflow starts: Generates UUID `batch_id` and records `start_time`
- When step 3 completes: Calls `recordWorkflowHistory()`
- API request sent to `POST /api/v1/stub/load-history`
- Success/failure logged in output console

**Verify deployment:**
```bash
# Start the frontend
cd pp-frontend
npm run dev

# Run a workflow:
# 1. Go to Stub → Load tab
# 2. Enter customer numbers (e.g., "123456789,987654321")
# 3. Click "작업 시작"
# 4. Wait for completion
# 5. Check output logs for: "[INFO] 작업 이력 저장 완료 (N건)"
```

### 3. Testing the System

**Test 1: Create History**
```bash
# Run a workflow with 3 customer numbers
# Expected: 3 rows inserted into database

curl -X POST http://localhost:8000/api/v1/stub/load-history \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_numbers": ["123456789", "987654321", "111111111"],
    "client_ip": "192.168.1.100",
    "execution_time_seconds": 45.5,
    "started_at": "2025-01-01T10:00:00Z",
    "completed_at": "2025-01-01T10:00:45Z"
  }'

# Expected response:
# {
#   "success": true,
#   "message": "작업 이력이 저장되었습니다 (3건)",
#   "batch_id": "550e8400-e29b-41d4-a716-446655440000",
#   "inserted_count": 3
# }
```

**Test 2: List History**
```bash
# Get recent history
curl http://localhost:8000/api/v1/stub/load-history?limit=10

# Expected response:
# {
#   "total": 3,
#   "items": [...]
# }
```

**Test 3: Batch Summary**
```bash
# Get batch summary
curl http://localhost:8000/api/v1/stub/load-history/batch/550e8400-e29b-41d4-a716-446655440000

# Expected response:
# {
#   "batch_id": "550e8400-e29b-41d4-a716-446655440000",
#   "total_customers": 3,
#   "client_ip": "192.168.1.100",
#   "execution_time_seconds": 45.5,
#   ...
# }
```

**Test 4: Customer History**
```bash
# Get specific customer history
curl http://localhost:8000/api/v1/stub/load-history/customer/123456789?limit=10

# Expected response: Array of history records for customer 123456789
```

**Test 5: Cleanup Old Records**
```bash
# Delete records older than 90 days
curl -X DELETE http://localhost:8000/api/v1/stub/load-history/cleanup?days=90

# Expected response:
# {
#   "success": true,
#   "message": "N건의 오래된 이력이 삭제되었습니다",
#   "deleted_count": N,
#   "retention_days": 90
# }
```

### 4. Database Management

**Location:**
```
pp-backend-fastapi/data/stub_history.db
```

**Manual Queries (SQLite CLI):**
```bash
# Open database
sqlite3 data/stub_history.db

# List all records
SELECT * FROM stub_load_history ORDER BY created_at DESC LIMIT 10;

# Count records by batch
SELECT batch_id, COUNT(*) as count
FROM stub_load_history
GROUP BY batch_id;

# Find records by customer number
SELECT * FROM stub_load_history
WHERE customer_number = '123456789';

# Get records from last 7 days
SELECT * FROM stub_load_history
WHERE created_at >= datetime('now', '-7 days');
```

**Backup Strategy:**
```bash
# Backup database (safe while app is running)
cp data/stub_history.db data/stub_history.db.backup.$(date +%Y%m%d)

# Or use SQLite backup command
sqlite3 data/stub_history.db ".backup 'data/stub_history.db.backup'"

# Restore from backup
cp data/stub_history.db.backup.20250101 data/stub_history.db
```

### 5. Production Considerations

**Disk Space Management:**
- Database grows by ~200 bytes per customer number
- 10,000 workflows × 10 customers = ~2MB
- Recommend monthly cleanup of old records:

```bash
# Schedule as cron job (keep last 90 days)
0 2 1 * * curl -X DELETE http://localhost:8000/api/v1/stub/load-history/cleanup?days=90
```

**Performance:**
- Indexes on batch_id, customer_number, client_ip ensure fast queries
- Pagination (limit/offset) prevents memory issues
- Async operations (aiosqlite) don't block other requests

**Monitoring:**
- Check database size: `ls -lh data/stub_history.db`
- Check record count: `sqlite3 data/stub_history.db "SELECT COUNT(*) FROM stub_load_history;"`
- Monitor logs for history recording failures

**Error Handling:**
- History recording failure does NOT affect workflow success
- Errors are logged and shown in output console
- Common issues:
  - Disk full: Clean up old records or increase disk space
  - Permissions: Ensure `data/` directory is writable
  - Duplicate entries: UNIQUE constraint prevents duplicates (expected behavior)

### 6. Integration with Existing Workflows

The system is **fully integrated** and requires **no changes** to existing code:

✅ **Automatic Recording**: History is saved after every successful workflow
✅ **No User Action**: Users don't need to do anything special
✅ **Non-Blocking**: History recording doesn't slow down workflows
✅ **Fault Tolerant**: Recording failures don't affect workflow success

**Frontend Changes Made:**
- `websocket.ts`: Added batch ID generation and history recording
- `stubApi.ts`: Created API client for history endpoints

**Backend Changes Made:**
- `main.py`: Added database initialization on startup
- `router.py`: Registered REST API endpoints
- Created service, schemas, and router files

## API Reference

### POST /api/v1/stub/load-history
Create work history (one row per customer number)

**Request Body:**
```json
{
  "batch_id": "uuid-string",
  "customer_numbers": ["123456789", "987654321"],
  "client_ip": "192.168.1.100",
  "connection_id": "optional-connection-id",
  "execution_time_seconds": 45.5,
  "started_at": "2025-01-01T10:00:00Z",
  "completed_at": "2025-01-01T10:00:45Z"
}
```

**Validation:**
- `customer_numbers`: 9 or 10 digit numbers, min 1 entry
- `execution_time_seconds`: > 0, < 86400 (24 hours)
- `started_at`, `completed_at`: ISO 8601 datetime strings

**Response:**
```json
{
  "success": true,
  "message": "작업 이력이 저장되었습니다 (2건)",
  "batch_id": "uuid-string",
  "inserted_count": 2
}
```

### GET /api/v1/stub/load-history
List work history with filters and pagination

**Query Parameters:**
- `customer_number` (optional): Filter by customer number
- `client_ip` (optional): Filter by client IP
- `batch_id` (optional): Filter by batch ID
- `limit` (optional, default=100, max=1000): Number of records
- `offset` (optional, default=0): Pagination offset

**Response:**
```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "batch_id": "uuid-string",
      "customer_number": "123456789",
      "client_ip": "192.168.1.100",
      "connection_id": "connection-id",
      "execution_time_seconds": 45.5,
      "started_at": "2025-01-01T10:00:00",
      "completed_at": "2025-01-01T10:00:45",
      "created_at": "2025-01-01T10:00:46"
    }
  ]
}
```

### GET /api/v1/stub/load-history/batch/{batch_id}
Get batch summary

**Response:**
```json
{
  "batch_id": "uuid-string",
  "total_customers": 10,
  "client_ip": "192.168.1.100",
  "execution_time_seconds": 45.5,
  "started_at": "2025-01-01T10:00:00",
  "completed_at": "2025-01-01T10:00:45",
  "created_at": "2025-01-01T10:00:46"
}
```

### GET /api/v1/stub/load-history/customer/{customer_number}
Get customer-specific history

**Query Parameters:**
- `limit` (optional, default=10, max=100): Number of records

**Response:**
```json
[
  {
    "id": 1,
    "batch_id": "uuid-string-1",
    ...
  },
  {
    "id": 2,
    "batch_id": "uuid-string-2",
    ...
  }
]
```

### DELETE /api/v1/stub/load-history/cleanup
Delete old records

**Query Parameters:**
- `days` (optional, default=90, min=30, max=365): Retention period

**Response:**
```json
{
  "success": true,
  "message": "5건의 오래된 이력이 삭제되었습니다",
  "deleted_count": 5,
  "retention_days": 90
}
```

## Troubleshooting

### Issue: Database initialization fails

**Symptoms:**
```
[StubLoadHistory] Failed to initialize database: [Errno 13] Permission denied
```

**Solution:**
```bash
# Ensure data directory exists and is writable
mkdir -p pp-backend-fastapi/data
chmod 755 pp-backend-fastapi/data
```

### Issue: History recording fails with "unknown" IP

**Symptoms:**
```
[WARNING] 작업 이력 저장 실패: ...
```

**Solution:**
This is normal for development. The backend will extract the real IP from the request. If you need a specific IP, modify `websocket.ts`:
```typescript
client_ip: '192.168.1.100', // instead of 'unknown'
```

### Issue: Duplicate entry error

**Symptoms:**
```
중복된 배치 ID 또는 고객번호가 존재합니다
```

**Solution:**
This is expected behavior (UNIQUE constraint). It means the same customer number in the same batch was already recorded. This prevents accidental duplicates.

### Issue: Frontend API call fails

**Symptoms:**
```
[STUB-WS] Failed to record history: Failed to fetch
```

**Solution:**
1. Check backend is running on port 8000
2. Check CORS configuration in backend
3. Verify API endpoint exists in Swagger docs
4. Check browser console for detailed error

## Summary

The Work History System is now **fully deployed and operational**. It will:

✅ Automatically record all successful workflows
✅ Store detailed execution metadata
✅ Provide RESTful API for querying history
✅ Support production deployment with minimal maintenance

No additional configuration or user action is required. The system is ready for production use.
