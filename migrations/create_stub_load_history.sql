-- ============================================
-- Stub Load History Table
-- 대응답 적재 작업 이력 테이블
-- ============================================

CREATE TABLE IF NOT EXISTS stub_load_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 작업 정보
    batch_id TEXT NOT NULL,                    -- 작업 배치 ID (UUID, 동일 작업에 대해 같은 값)
    customer_number TEXT NOT NULL,             -- 고객번호 (9자리 또는 10자리)

    -- 클라이언트 정보
    client_ip TEXT NOT NULL,                   -- 클라이언트 IP 주소
    connection_id TEXT,                        -- WebSocket 연결 ID

    -- 작업 시간 정보
    execution_time_seconds REAL NOT NULL,      -- 작업 소요 시간 (초 단위, 소수점 포함)
    started_at TEXT NOT NULL,                  -- 작업 시작 시간 (ISO 8601 format)
    completed_at TEXT NOT NULL,                -- 작업 완료 시간 (ISO 8601 format)

    -- 메타데이터
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 레코드 생성 시간
    updated_at TEXT,                                      -- 레코드 수정 시간
    note TEXT,                                            -- 작업 이력 메모/설명

    -- 인덱스를 위한 제약조건
    UNIQUE(batch_id, customer_number)          -- 동일 배치에서 중복 고객번호 방지
);

-- 인덱스 생성 (조회 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_stub_load_history_batch_id
    ON stub_load_history(batch_id);

CREATE INDEX IF NOT EXISTS idx_stub_load_history_customer_number
    ON stub_load_history(customer_number);

CREATE INDEX IF NOT EXISTS idx_stub_load_history_client_ip
    ON stub_load_history(client_ip);

CREATE INDEX IF NOT EXISTS idx_stub_load_history_created_at
    ON stub_load_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_stub_load_history_completed_at
    ON stub_load_history(completed_at DESC);

CREATE INDEX IF NOT EXISTS idx_stub_load_history_updated_at
    ON stub_load_history(updated_at DESC);

-- ============================================
-- 사용 예시
-- ============================================
--
-- 1. 작업 이력 조회 (최근 100건)
-- SELECT * FROM stub_load_history
-- ORDER BY created_at DESC
-- LIMIT 100;
--
-- 2. 특정 고객번호 이력 조회
-- SELECT * FROM stub_load_history
-- WHERE customer_number = '123456789'
-- ORDER BY created_at DESC;
--
-- 3. 특정 배치의 모든 고객번호 조회
-- SELECT * FROM stub_load_history
-- WHERE batch_id = 'uuid-here'
-- ORDER BY customer_number;
--
-- 4. 특정 IP의 작업 이력
-- SELECT * FROM stub_load_history
-- WHERE client_ip = '192.168.1.100'
-- ORDER BY created_at DESC;
--
-- ============================================
