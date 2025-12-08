"""
Stub Load History Repository
대응답 적재 작업 이력 데이터 액세스 레이어
"""

import aiosqlite
from typing import List, Optional
from pathlib import Path

from app.core.logger import logger
from app.core.exceptions.base import (
    StubLoadHistoryDBConnectionException,
    StubLoadHistoryDBInitException,
    StubLoadHistoryCreateException,
    StubLoadHistoryQueryException,
    StubLoadHistoryDeleteException,
    StubLoadHistoryDuplicateException,
)
from app.domains.stub.models.load_history import StubLoadHistory


class StubLoadHistoryRepository:
    """대응답 적재 작업 이력 Repository"""

    def __init__(self, db_path: str = "data/stub_history.db"):
        """
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        """데이터베이스 디렉토리 생성"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    async def _get_connection(self) -> aiosqlite.Connection:
        """데이터베이스 연결 획득"""
        try:
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            return conn
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to connect to database: {e}", exc_info=True)
            raise StubLoadHistoryDBConnectionException(
                db_path=self.db_path,
                detail=str(e),
                original_exception=e
            )

    async def initialize_db(self) -> None:
        """데이터베이스 초기화 (테이블 생성)"""
        try:
            async with await self._get_connection() as db:
                # 테이블 생성
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS stub_load_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id TEXT NOT NULL,
                        customer_number TEXT NOT NULL,
                        client_ip TEXT NOT NULL,
                        connection_id TEXT,
                        execution_time_seconds REAL NOT NULL,
                        started_at TEXT NOT NULL,
                        completed_at TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT,
                        note TEXT,
                        UNIQUE(batch_id, customer_number)
                    )
                """)

                # 인덱스 생성
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_stub_load_history_batch_id ON stub_load_history(batch_id)",
                    "CREATE INDEX IF NOT EXISTS idx_stub_load_history_customer_number ON stub_load_history(customer_number)",
                    "CREATE INDEX IF NOT EXISTS idx_stub_load_history_client_ip ON stub_load_history(client_ip)",
                    "CREATE INDEX IF NOT EXISTS idx_stub_load_history_created_at ON stub_load_history(created_at DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_stub_load_history_completed_at ON stub_load_history(completed_at DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_stub_load_history_updated_at ON stub_load_history(updated_at DESC)",
                ]

                for index_sql in indexes:
                    await db.execute(index_sql)

                await db.commit()
                logger.info("[LoadHistoryRepo] Database initialized successfully")

        except StubLoadHistoryDBConnectionException:
            raise
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to initialize database: {e}", exc_info=True)
            raise StubLoadHistoryDBInitException(
                db_path=self.db_path,
                detail=str(e),
                original_exception=e
            )

    async def create_bulk(self, histories: List[StubLoadHistory]) -> int:
        """
        여러 작업 이력을 일괄 생성

        Args:
            histories: 생성할 이력 목록

        Returns:
            생성된 레코드 수
        """
        try:
            async with await self._get_connection() as db:
                inserted_count = 0

                for history in histories:
                    await db.execute(
                        """
                        INSERT INTO stub_load_history (
                            batch_id, customer_number, client_ip, connection_id,
                            execution_time_seconds, started_at, completed_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            history.batch_id,
                            history.customer_number,
                            history.client_ip,
                            history.connection_id,
                            history.execution_time_seconds,
                            history.started_at,
                            history.completed_at,
                        ),
                    )
                    inserted_count += 1

                await db.commit()
                logger.info(f"[LoadHistoryRepo] Created {inserted_count} records")
                return inserted_count

        except aiosqlite.IntegrityError as e:
            logger.warning(f"[LoadHistoryRepo] Duplicate entry detected: {e}")
            raise StubLoadHistoryDuplicateException(
                detail="중복된 배치 ID 또는 고객번호가 존재합니다",
                original_exception=e
            )
        except StubLoadHistoryDBConnectionException:
            raise
        except StubLoadHistoryDuplicateException:
            raise
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to create histories: {e}", exc_info=True)
            raise StubLoadHistoryCreateException(
                detail=str(e),
                original_exception=e
            )

    async def find_by_id(self, history_id: int) -> Optional[StubLoadHistory]:
        """
        ID로 단일 이력 조회

        Args:
            history_id: 이력 ID

        Returns:
            이력 모델 또는 None
        """
        try:
            async with await self._get_connection() as db:
                async with db.execute(
                    "SELECT * FROM stub_load_history WHERE id = ?",
                    (history_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return StubLoadHistory.from_db_row(dict(row))
                    return None

        except StubLoadHistoryDBConnectionException:
            raise
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to find by ID: {e}", exc_info=True)
            raise StubLoadHistoryQueryException(
                query_type="find_by_id",
                filters={"history_id": history_id},
                detail=str(e),
                original_exception=e
            )

    async def find_all(
        self,
        customer_number: Optional[str] = None,
        client_ip: Optional[str] = None,
        batch_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[StubLoadHistory], int]:
        """
        조건에 맞는 이력 목록 조회

        Args:
            customer_number: 고객번호 필터
            client_ip: IP 필터
            batch_id: 배치 ID 필터
            limit: 조회 개수
            offset: 오프셋

        Returns:
            (이력 목록, 전체 개수) 튜플
        """
        try:
            async with await self._get_connection() as db:
                # WHERE 절 구성
                where_clauses = []
                params = []

                if customer_number:
                    where_clauses.append("customer_number = ?")
                    params.append(customer_number)
                if client_ip:
                    where_clauses.append("client_ip = ?")
                    params.append(client_ip)
                if batch_id:
                    where_clauses.append("batch_id = ?")
                    params.append(batch_id)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                # 전체 개수 조회
                count_query = f"SELECT COUNT(*) as total FROM stub_load_history {where_sql}"
                async with db.execute(count_query, params) as cursor:
                    row = await cursor.fetchone()
                    total = row["total"] if row else 0

                # 데이터 조회
                data_query = f"""
                    SELECT * FROM stub_load_history
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """
                async with db.execute(data_query, params + [limit, offset]) as cursor:
                    rows = await cursor.fetchall()
                    histories = [StubLoadHistory.from_db_row(dict(row)) for row in rows]

                return histories, total

        except StubLoadHistoryDBConnectionException:
            raise
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to find all: {e}", exc_info=True)
            filters = {}
            if customer_number:
                filters["customer_number"] = customer_number
            if client_ip:
                filters["client_ip"] = client_ip
            if batch_id:
                filters["batch_id"] = batch_id
            raise StubLoadHistoryQueryException(
                query_type="find_all",
                filters=filters,
                detail=str(e),
                original_exception=e
            )

    async def find_by_batch_id(self, batch_id: str) -> List[StubLoadHistory]:
        """
        배치 ID로 모든 이력 조회

        Args:
            batch_id: 배치 ID

        Returns:
            이력 목록
        """
        try:
            async with await self._get_connection() as db:
                async with db.execute(
                    "SELECT * FROM stub_load_history WHERE batch_id = ? ORDER BY customer_number",
                    (batch_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [StubLoadHistory.from_db_row(dict(row)) for row in rows]

        except StubLoadHistoryDBConnectionException:
            raise
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to find by batch ID: {e}", exc_info=True)
            raise StubLoadHistoryQueryException(
                query_type="find_by_batch_id",
                filters={"batch_id": batch_id},
                detail=str(e),
                original_exception=e
            )

    async def find_by_customer_number(
        self, customer_number: str, limit: int = 10
    ) -> List[StubLoadHistory]:
        """
        고객번호로 이력 조회

        Args:
            customer_number: 고객번호
            limit: 조회 개수

        Returns:
            이력 목록
        """
        histories, _ = await self.find_all(customer_number=customer_number, limit=limit, offset=0)
        return histories

    async def update_note(self, history_id: int, note: str) -> bool:
        """
        이력 메모 업데이트

        Args:
            history_id: 이력 ID
            note: 메모 내용

        Returns:
            업데이트 성공 여부
        """
        try:
            async with await self._get_connection() as db:
                cursor = await db.execute(
                    """
                    UPDATE stub_load_history
                    SET note = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (note, history_id)
                )
                await db.commit()

                if cursor.rowcount > 0:
                    logger.info(f"[LoadHistoryRepo] Updated note for history ID {history_id}")
                    return True
                return False

        except StubLoadHistoryDBConnectionException:
            raise
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to update note: {e}", exc_info=True)
            raise StubLoadHistoryQueryException(
                query_type="update_note",
                filters={"history_id": history_id},
                detail=str(e),
                original_exception=e
            )

    async def delete_older_than(self, days: int = 90) -> int:
        """
        오래된 레코드 삭제

        Args:
            days: 보관 일수

        Returns:
            삭제된 레코드 수
        """
        try:
            async with await self._get_connection() as db:
                cursor = await db.execute(
                    """
                    DELETE FROM stub_load_history
                    WHERE created_at < datetime('now', ?)
                    """,
                    (f"-{days} days",)
                )
                deleted_count = cursor.rowcount
                await db.commit()

                logger.info(f"[LoadHistoryRepo] Deleted {deleted_count} old records (>{days} days)")
                return deleted_count

        except StubLoadHistoryDBConnectionException:
            raise
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to delete old records: {e}", exc_info=True)
            raise StubLoadHistoryDeleteException(
                retention_days=days,
                detail=str(e),
                original_exception=e
            )
