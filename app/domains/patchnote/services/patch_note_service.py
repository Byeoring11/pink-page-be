"""
Patch Note Service
패치 노트 비즈니스 로직 레이어
"""

from datetime import date
from typing import List, Optional

from app.core.logger import logger
from app.core.exceptions.base import (
    PatchNoteNotFoundException,
    PatchNoteValidationException,
)
from app.domains.patchnote.repositories.patch_note_repository import PatchNoteRepository
from app.domains.patchnote.models.patch_note import PatchNote
from app.domains.patchnote.schemas.patch_note_schemas import (
    PatchNoteCreateRequest,
    PatchNoteUpdateRequest,
    PatchNoteResponse,
    PatchNoteListResponse,
)


class PatchNoteService:
    """패치 노트 서비스"""

    def __init__(self, repository: Optional[PatchNoteRepository] = None):
        """
        Args:
            repository: Repository 인스턴스 (의존성 주입)
        """
        self.repository = repository or PatchNoteRepository()

    async def initialize(self) -> None:
        """서비스 초기화 (DB 초기화)"""
        await self.repository.initialize_db()

    async def create_patch_note(self, request: PatchNoteCreateRequest) -> int:
        """
        패치 노트 생성

        Args:
            request: 패치 노트 생성 요청

        Returns:
            생성된 패치 노트 ID
        """
        # Validation
        if len(request.title.strip()) == 0:
            raise PatchNoteValidationException(
                field="title",
                value=request.title,
                detail="제목은 빈 문자열일 수 없습니다"
            )

        if len(request.content.strip()) == 0:
            raise PatchNoteValidationException(
                field="content",
                value=request.content,
                detail="내용은 빈 문자열일 수 없습니다"
            )

        # 모델 생성
        patch_note = PatchNote(
            title=request.title,
            content=request.content,
            patch_date=request.patch_date,
        )

        # Repository를 통해 저장
        created = await self.repository.create(patch_note)
        logger.info(f"[PatchNoteService] Created patch note with ID {created.id}")

        return created.id

    async def get_patch_note_by_id(self, patch_note_id: int) -> Optional[PatchNoteResponse]:
        """
        ID로 패치 노트 조회

        Args:
            patch_note_id: 패치 노트 ID

        Returns:
            패치 노트 또는 None
        """
        patch_note = await self.repository.find_by_id(patch_note_id)
        if patch_note:
            return PatchNoteResponse(**patch_note.to_dict())
        return None

    async def get_patch_notes(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> PatchNoteListResponse:
        """
        패치 노트 목록 조회

        Args:
            start_date: 시작 날짜 필터
            end_date: 종료 날짜 필터
            limit: 조회 개수
            offset: 오프셋

        Returns:
            패치 노트 목록 및 전체 개수
        """
        if start_date or end_date:
            patch_notes, total = await self.repository.find_by_date_range(
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
            )
        else:
            patch_notes, total = await self.repository.find_all(
                limit=limit,
                offset=offset,
            )

        items = [PatchNoteResponse(**p.to_dict()) for p in patch_notes]
        logger.info(f"[PatchNoteService] Retrieved {len(items)} patch notes (total: {total})")

        return PatchNoteListResponse(total=total, items=items)

    async def update_patch_note(
        self, patch_note_id: int, request: PatchNoteUpdateRequest
    ) -> bool:
        """
        패치 노트 수정

        Args:
            patch_note_id: 패치 노트 ID
            request: 수정 요청

        Returns:
            수정 성공 여부

        Raises:
            PatchNoteNotFoundException: 패치 노트를 찾을 수 없음
        """
        # 패치 노트 존재 확인
        patch_note = await self.repository.find_by_id(patch_note_id)
        if not patch_note:
            raise PatchNoteNotFoundException(patch_note_id=patch_note_id)

        # Validation
        if request.title is not None and len(request.title.strip()) == 0:
            raise PatchNoteValidationException(
                field="title",
                value=request.title,
                detail="제목은 빈 문자열일 수 없습니다"
            )

        if request.content is not None and len(request.content.strip()) == 0:
            raise PatchNoteValidationException(
                field="content",
                value=request.content,
                detail="내용은 빈 문자열일 수 없습니다"
            )

        # 업데이트
        success = await self.repository.update(
            patch_note_id=patch_note_id,
            title=request.title,
            content=request.content,
            patch_date=request.patch_date,
        )

        if success:
            logger.info(f"[PatchNoteService] Updated patch note ID {patch_note_id}")

        return success

    async def delete_patch_note(self, patch_note_id: int) -> bool:
        """
        패치 노트 삭제

        Args:
            patch_note_id: 패치 노트 ID

        Returns:
            삭제 성공 여부

        Raises:
            PatchNoteNotFoundException: 패치 노트를 찾을 수 없음
        """
        # 패치 노트 존재 확인
        patch_note = await self.repository.find_by_id(patch_note_id)
        if not patch_note:
            raise PatchNoteNotFoundException(patch_note_id=patch_note_id)

        # 삭제
        success = await self.repository.delete(patch_note_id)

        if success:
            logger.info(f"[PatchNoteService] Deleted patch note ID {patch_note_id}")

        return success
