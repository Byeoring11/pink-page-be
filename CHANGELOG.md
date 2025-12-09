# Changelog

## 2025-12-09

### Added
- **Patch Note 도메인 추가**
  - 패치 노트 CRUD REST API (`/api/v1/patchnotes`)
  - 도메인 레이어 구현 (model, schema, repository, service, router)
  - 예외 처리 시스템 (54000-54005 에러 코드)
  - SQLite 데이터베이스 자동 초기화

### Changed
- **한국 시간(KST) 적용**
  - 모든 timestamp 필드를 한국 시간으로 변경
  - `datetime.utcnow()` (deprecated) → `datetime.now(ZoneInfo("Asia/Seoul"))`
  - 적용 대상:
    - `app/domains/patchnote/models/patch_note.py`
    - `app/domains/patchnote/repositories/patch_note_repository.py`
    - `app/domains/stub/models/load_history.py`
    - `app/domains/stub/repositories/load_history_repository.py`

### Technical Details

#### Patch Note API Endpoints
- `POST /api/v1/patchnotes` - 패치 노트 생성
- `GET /api/v1/patchnotes` - 패치 노트 목록 조회 (필터링, 페이지네이션)
- `GET /api/v1/patchnotes/{id}` - 단일 패치 노트 조회
- `PATCH /api/v1/patchnotes/{id}` - 패치 노트 수정
- `DELETE /api/v1/patchnotes/{id}` - 패치 노트 삭제

#### Database Schema
```sql
CREATE TABLE patch_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    patch_date DATE NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME
);
```

#### Exception Codes
- 54000: Patch note creation failed
- 54001: Patch note query failed
- 54002: Patch note not found
- 54003: Patch note deletion failed
- 54004: Patch note validation error
- 54005: Patch note database connection failed

#### Architecture
- Repository Pattern: Data access layer abstraction
- Service Layer: Business logic separation
- Exception Hierarchy: Custom exception classes with structured error codes
- Async SQLAlchemy: Non-blocking database operations
