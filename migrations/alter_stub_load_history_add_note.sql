-- ============================================
-- Stub Load History Table - Add Note Field
-- 대응답 적재 작업 이력 테이블 - 메모 필드 추가
-- ============================================

-- Add note column for user comments/descriptions
ALTER TABLE stub_load_history ADD COLUMN note TEXT DEFAULT NULL;

-- Add updated_at column to track record modifications
ALTER TABLE stub_load_history ADD COLUMN updated_at TEXT DEFAULT NULL;

-- Create index on updated_at for efficient queries
CREATE INDEX IF NOT EXISTS idx_stub_load_history_updated_at
    ON stub_load_history(updated_at DESC);

-- ============================================
-- 사용 예시
-- ============================================
--
-- 1. 특정 이력에 메모 추가/수정
-- UPDATE stub_load_history
-- SET note = '고객 요청으로 긴급 처리함',
--     updated_at = datetime('now')
-- WHERE id = 1;
--
-- 2. 메모가 있는 이력 조회
-- SELECT * FROM stub_load_history
-- WHERE note IS NOT NULL
-- ORDER BY updated_at DESC;
--
-- ============================================
