"""
Stub Load History Repository
대응답 적재 작업 이력 데이터 액세스 레이어 (SQLAlchemy ORM)
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, func, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.db.session import session as db_session, engine
from app.db.base import Base


class StubLoadHistoryRepository:
    """대응답 적재 작업 이력 Repository (SQLAlchemy)"""

    def __init__(self):
        """Repository 초기화"""
        pass

    async def initialize_db(self) -> None:
        """
        데이터베이스 초기화 (테이블 생성)

        SQLAlchemy의 create_all을 사용하여 모든 테이블 생성
        """
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("[LoadHistoryRepo] Database initialized successfully")
        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to initialize database: {e}", exc_info=True)
            raise StubLoadHistoryDBInitException(
                db_path=str(engine.url),
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
        session: AsyncSession = db_session()
        try:
            session.add_all(histories)
            await session.commit()

            inserted_count = len(histories)
            logger.info(f"[LoadHistoryRepo] Created {inserted_count} records")
            return inserted_count

        except IntegrityError as e:
            await session.rollback()
            logger.warning(f"[LoadHistoryRepo] Duplicate entry detected: {e}")
            raise StubLoadHistoryDuplicateException(
                detail="중복된 배치 ID 또는 고객번호가 존재합니다",
                original_exception=e
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"[LoadHistoryRepo] Failed to create histories: {e}", exc_info=True)
            raise StubLoadHistoryCreateException(
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def find_by_id(self, history_id: int) -> Optional[StubLoadHistory]:
        """
        ID로 단일 이력 조회

        Args:
            history_id: 이력 ID

        Returns:
            이력 모델 또는 None
        """
        session: AsyncSession = db_session()
        try:
            stmt = select(StubLoadHistory).where(StubLoadHistory.id == history_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to find by ID: {e}", exc_info=True)
            raise StubLoadHistoryQueryException(
                query_type="find_by_id",
                filters={"history_id": history_id},
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def find_all(
        self,
        customer_number: Optional[str] = None,
        client_ip: Optional[str] = None,
        note: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[StubLoadHistory], int]:
        """
        조건에 맞는 이력 목록 조회

        Args:
            customer_number: 고객번호 필터
            client_ip: IP 필터
            note: Note 내용 필터 (LIKE 검색)
            limit: 조회 개수
            offset: 오프셋

        Returns:
            (이력 목록, 전체 개수) 튜플
        """
        session: AsyncSession = db_session()
        try:
            # WHERE 절 구성
            conditions = []
            if customer_number:
                conditions.append(StubLoadHistory.customer_number == customer_number)
            if client_ip:
                conditions.append(StubLoadHistory.client_ip == client_ip)
            if note:
                conditions.append(StubLoadHistory.note.like(f"%{note}%"))

            # 전체 개수 조회
            count_stmt = select(func.count()).select_from(StubLoadHistory)
            if conditions:
                count_stmt = count_stmt.where(*conditions)

            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 데이터 조회
            data_stmt = select(StubLoadHistory)
            if conditions:
                data_stmt = data_stmt.where(*conditions)

            data_stmt = data_stmt.order_by(StubLoadHistory.created_at.desc()).limit(limit).offset(offset)

            data_result = await session.execute(data_stmt)
            histories = list(data_result.scalars().all())

            return histories, total

        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to find all: {e}", exc_info=True)
            filters = {}
            if customer_number:
                filters["customer_number"] = customer_number
            if client_ip:
                filters["client_ip"] = client_ip
            if note:
                filters["note"] = note
            raise StubLoadHistoryQueryException(
                query_type="find_all",
                filters=filters,
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def find_by_batch_id(self, batch_id: str) -> List[StubLoadHistory]:
        """
        배치 ID로 모든 이력 조회

        Args:
            batch_id: 배치 ID

        Returns:
            이력 목록
        """
        session: AsyncSession = db_session()
        try:
            stmt = select(StubLoadHistory).where(
                StubLoadHistory.batch_id == batch_id
            ).order_by(StubLoadHistory.customer_number)

            result = await session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"[LoadHistoryRepo] Failed to find by batch ID: {e}", exc_info=True)
            raise StubLoadHistoryQueryException(
                query_type="find_by_batch_id",
                filters={"batch_id": batch_id},
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

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
        session: AsyncSession = db_session()
        try:
            stmt = update(StubLoadHistory).where(
                StubLoadHistory.id == history_id
            ).values(
                note=note,
                updated_at=datetime.utcnow()
            )

            result = await session.execute(stmt)
            await session.commit()

            if result.rowcount > 0:
                logger.info(f"[LoadHistoryRepo] Updated note for history ID {history_id}")
                return True
            return False

        except Exception as e:
            await session.rollback()
            logger.error(f"[LoadHistoryRepo] Failed to update note: {e}", exc_info=True)
            raise StubLoadHistoryQueryException(
                query_type="update_note",
                filters={"history_id": history_id},
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def delete_older_than(self, days: int = 90) -> int:
        """
        오래된 레코드 삭제

        Args:
            days: 보관 일수

        Returns:
            삭제된 레코드 수
        """
        session: AsyncSession = db_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            stmt = delete(StubLoadHistory).where(
                StubLoadHistory.created_at < cutoff_date
            )

            result = await session.execute(stmt)
            await session.commit()

            deleted_count = result.rowcount
            logger.info(f"[LoadHistoryRepo] Deleted {deleted_count} old records (>{days} days)")
            return deleted_count

        except Exception as e:
            await session.rollback()
            logger.error(f"[LoadHistoryRepo] Failed to delete old records: {e}", exc_info=True)
            raise StubLoadHistoryDeleteException(
                retention_days=days,
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()
