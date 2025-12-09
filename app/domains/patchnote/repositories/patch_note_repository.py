"""
Patch Note Repository
패치 노트 데이터 액세스 레이어 (SQLAlchemy ORM)
"""

from datetime import datetime, date
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.exceptions.base import (
    PatchNoteDBConnectionException,
    PatchNoteCreateException,
    PatchNoteQueryException,
    PatchNoteDeleteException,
)
from app.domains.patchnote.models.patch_note import PatchNote
from app.db.session import session as db_session, engine
from app.db.base import Base


class PatchNoteRepository:
    """패치 노트 Repository (SQLAlchemy)"""

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
            logger.info("[PatchNoteRepo] Database initialized successfully")
        except Exception as e:
            logger.error(f"[PatchNoteRepo] Failed to initialize database: {e}", exc_info=True)
            raise PatchNoteDBConnectionException(
                db_path=str(engine.url),
                detail=str(e),
                original_exception=e
            )

    async def create(self, patch_note: PatchNote) -> PatchNote:
        """
        패치 노트 생성

        Args:
            patch_note: 생성할 패치 노트

        Returns:
            생성된 패치 노트
        """
        session: AsyncSession = db_session()
        try:
            session.add(patch_note)
            await session.commit()
            await session.refresh(patch_note)

            logger.info(f"[PatchNoteRepo] Created patch note with ID {patch_note.id}")
            return patch_note

        except IntegrityError as e:
            await session.rollback()
            logger.error(f"[PatchNoteRepo] Integrity error: {e}", exc_info=True)
            raise PatchNoteCreateException(
                title=patch_note.title,
                detail="데이터 무결성 오류가 발생했습니다",
                original_exception=e
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"[PatchNoteRepo] Failed to create patch note: {e}", exc_info=True)
            raise PatchNoteCreateException(
                title=patch_note.title,
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def find_by_id(self, patch_note_id: int) -> Optional[PatchNote]:
        """
        ID로 패치 노트 조회

        Args:
            patch_note_id: 패치 노트 ID

        Returns:
            패치 노트 또는 None
        """
        session: AsyncSession = db_session()
        try:
            stmt = select(PatchNote).where(PatchNote.id == patch_note_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"[PatchNoteRepo] Failed to find by ID: {e}", exc_info=True)
            raise PatchNoteQueryException(
                query_type="find_by_id",
                filters={"patch_note_id": patch_note_id},
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[PatchNote], int]:
        """
        모든 패치 노트 조회 (최신순)

        Args:
            limit: 조회 개수
            offset: 오프셋

        Returns:
            (패치 노트 목록, 전체 개수) 튜플
        """
        session: AsyncSession = db_session()
        try:
            # 전체 개수 조회
            count_stmt = select(func.count()).select_from(PatchNote)
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 데이터 조회 (최신순: patch_date desc, created_at desc)
            data_stmt = (
                select(PatchNote)
                .order_by(PatchNote.patch_date.desc(), PatchNote.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            data_result = await session.execute(data_stmt)
            patch_notes = list(data_result.scalars().all())

            return patch_notes, total

        except Exception as e:
            logger.error(f"[PatchNoteRepo] Failed to find all: {e}", exc_info=True)
            raise PatchNoteQueryException(
                query_type="find_all",
                filters={"limit": limit, "offset": offset},
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def find_by_date_range(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[PatchNote], int]:
        """
        날짜 범위로 패치 노트 조회

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 조회 개수
            offset: 오프셋

        Returns:
            (패치 노트 목록, 전체 개수) 튜플
        """
        session: AsyncSession = db_session()
        try:
            # WHERE 절 구성
            conditions = []
            if start_date:
                conditions.append(PatchNote.patch_date >= start_date)
            if end_date:
                conditions.append(PatchNote.patch_date <= end_date)

            # 전체 개수 조회
            count_stmt = select(func.count()).select_from(PatchNote)
            if conditions:
                count_stmt = count_stmt.where(*conditions)

            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # 데이터 조회
            data_stmt = select(PatchNote)
            if conditions:
                data_stmt = data_stmt.where(*conditions)

            data_stmt = (
                data_stmt
                .order_by(PatchNote.patch_date.desc(), PatchNote.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            data_result = await session.execute(data_stmt)
            patch_notes = list(data_result.scalars().all())

            return patch_notes, total

        except Exception as e:
            logger.error(f"[PatchNoteRepo] Failed to find by date range: {e}", exc_info=True)
            raise PatchNoteQueryException(
                query_type="find_by_date_range",
                filters={"start_date": start_date, "end_date": end_date},
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def update(
        self,
        patch_note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        patch_date: Optional[date] = None,
    ) -> bool:
        """
        패치 노트 업데이트

        Args:
            patch_note_id: 패치 노트 ID
            title: 업데이트할 타이틀
            content: 업데이트할 내용
            patch_date: 업데이트할 패치 날짜

        Returns:
            업데이트 성공 여부
        """
        session: AsyncSession = db_session()
        try:
            # 업데이트할 필드 구성
            values = {"updated_at": datetime.now(ZoneInfo("Asia/Seoul"))}
            if title is not None:
                values["title"] = title
            if content is not None:
                values["content"] = content
            if patch_date is not None:
                values["patch_date"] = patch_date

            stmt = (
                update(PatchNote)
                .where(PatchNote.id == patch_note_id)
                .values(**values)
            )

            result = await session.execute(stmt)
            await session.commit()

            if result.rowcount > 0:
                logger.info(f"[PatchNoteRepo] Updated patch note ID {patch_note_id}")
                return True
            return False

        except Exception as e:
            await session.rollback()
            logger.error(f"[PatchNoteRepo] Failed to update patch note: {e}", exc_info=True)
            raise PatchNoteQueryException(
                query_type="update",
                filters={"patch_note_id": patch_note_id},
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()

    async def delete(self, patch_note_id: int) -> bool:
        """
        패치 노트 삭제

        Args:
            patch_note_id: 패치 노트 ID

        Returns:
            삭제 성공 여부
        """
        session: AsyncSession = db_session()
        try:
            stmt = delete(PatchNote).where(PatchNote.id == patch_note_id)

            result = await session.execute(stmt)
            await session.commit()

            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"[PatchNoteRepo] Deleted patch note ID {patch_note_id}")
                return True
            return False

        except Exception as e:
            await session.rollback()
            logger.error(f"[PatchNoteRepo] Failed to delete patch note: {e}", exc_info=True)
            raise PatchNoteDeleteException(
                patch_note_id=patch_note_id,
                detail=str(e),
                original_exception=e
            )
        finally:
            await session.close()
