"""
Patch Note REST API Router
패치 노트 REST API 엔드포인트
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import Optional

from app.core.logger import logger
from app.core.exceptions.base import (
    PatchNoteException,
    PatchNoteNotFoundException,
    PatchNoteValidationException,
    PatchNoteDBConnectionException,
)
from app.domains.patchnote.schemas.patch_note_schemas import (
    PatchNoteCreateRequest,
    PatchNoteUpdateRequest,
    PatchNoteResponse,
    PatchNoteListResponse,
    PatchNoteCreateResponse,
    PatchNoteDeleteResponse,
)
from app.domains.patchnote.services.patch_note_service import PatchNoteService

router = APIRouter(prefix="/patchnotes", tags=["PatchNote"])

# Service 싱글톤
_service: Optional[PatchNoteService] = None


def get_service() -> PatchNoteService:
    """서비스 의존성 주입"""
    global _service
    if _service is None:
        _service = PatchNoteService()
    return _service


@router.post("", response_model=PatchNoteCreateResponse, status_code=201)
async def create_patch_note(
    request_body: PatchNoteCreateRequest,
    service: PatchNoteService = Depends(get_service),
):
    """
    패치 노트 생성

    - 제목, 내용, 패치 날짜를 입력받아 새로운 패치 노트 생성
    """
    try:
        patch_note_id = await service.create_patch_note(request_body)

        logger.info(f"[PATCHNOTE-API] Created patch note with ID {patch_note_id}")

        return PatchNoteCreateResponse(
            success=True,
            message="패치 노트가 생성되었습니다",
            patch_note_id=patch_note_id,
        )

    except PatchNoteValidationException as e:
        logger.warning(f"[PATCHNOTE-API] Validation error: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or str(e))
    except PatchNoteDBConnectionException as e:
        logger.error(f"[PATCHNOTE-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except PatchNoteException as e:
        logger.error(f"[PATCHNOTE-API] Patch note error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "패치 노트 생성에 실패했습니다")
    except Exception as e:
        logger.error(f"[PATCHNOTE-API] Unexpected error creating patch note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="패치 노트 생성 중 예상치 못한 오류가 발생했습니다")


@router.get("", response_model=PatchNoteListResponse)
async def get_patch_notes(
    start_date: Optional[date] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="조회 개수 제한"),
    offset: int = Query(0, ge=0, description="오프셋"),
    service: PatchNoteService = Depends(get_service),
):
    """
    패치 노트 목록 조회

    - 필터 없이 조회 시: 최신순으로 전체 조회
    - 날짜 범위로 필터링 가능
    - 페이징 지원 (limit/offset)
    """
    try:
        result = await service.get_patch_notes(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        logger.info(f"[PATCHNOTE-API] Retrieved {len(result.items)} patch notes (total: {result.total})")
        return result

    except PatchNoteDBConnectionException as e:
        logger.error(f"[PATCHNOTE-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except PatchNoteException as e:
        logger.error(f"[PATCHNOTE-API] Patch note query error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "패치 노트 조회에 실패했습니다")
    except Exception as e:
        logger.error(f"[PATCHNOTE-API] Unexpected error getting patch notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="패치 노트 조회 중 예상치 못한 오류가 발생했습니다")


@router.get("/{patch_note_id}", response_model=PatchNoteResponse)
async def get_patch_note_by_id(
    patch_note_id: int = Path(..., description="패치 노트 ID"),
    service: PatchNoteService = Depends(get_service),
):
    """
    단일 패치 노트 조회

    - ID로 특정 패치 노트 조회
    """
    try:
        patch_note = await service.get_patch_note_by_id(patch_note_id)

        if not patch_note:
            raise HTTPException(status_code=404, detail=f"패치 노트 ID {patch_note_id}를 찾을 수 없습니다")

        logger.info(f"[PATCHNOTE-API] Retrieved patch note ID {patch_note_id}")
        return patch_note

    except HTTPException:
        raise
    except PatchNoteDBConnectionException as e:
        logger.error(f"[PATCHNOTE-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except PatchNoteException as e:
        logger.error(f"[PATCHNOTE-API] Patch note query error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "패치 노트 조회에 실패했습니다")
    except Exception as e:
        logger.error(f"[PATCHNOTE-API] Unexpected error getting patch note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="패치 노트 조회 중 예상치 못한 오류가 발생했습니다")


@router.patch("/{patch_note_id}", response_model=PatchNoteResponse)
async def update_patch_note(
    patch_note_id: int = Path(..., description="패치 노트 ID"),
    request_body: PatchNoteUpdateRequest = ...,
    service: PatchNoteService = Depends(get_service),
):
    """
    패치 노트 수정

    - 제목, 내용, 패치 날짜 수정 가능
    - 수정하지 않을 필드는 null로 전달
    """
    try:
        success = await service.update_patch_note(patch_note_id, request_body)

        if not success:
            raise HTTPException(status_code=404, detail=f"패치 노트 ID {patch_note_id}를 찾을 수 없습니다")

        logger.info(f"[PATCHNOTE-API] Updated patch note ID {patch_note_id}")

        # 업데이트 후 조회
        updated = await service.get_patch_note_by_id(patch_note_id)
        return updated

    except HTTPException:
        raise
    except PatchNoteNotFoundException as e:
        logger.warning(f"[PATCHNOTE-API] Patch note not found: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or "패치 노트를 찾을 수 없습니다")
    except PatchNoteValidationException as e:
        logger.warning(f"[PATCHNOTE-API] Validation error: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or str(e))
    except PatchNoteDBConnectionException as e:
        logger.error(f"[PATCHNOTE-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except PatchNoteException as e:
        logger.error(f"[PATCHNOTE-API] Patch note update error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "패치 노트 수정에 실패했습니다")
    except Exception as e:
        logger.error(f"[PATCHNOTE-API] Unexpected error updating patch note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="패치 노트 수정 중 예상치 못한 오류가 발생했습니다")


@router.delete("/{patch_note_id}", response_model=PatchNoteDeleteResponse)
async def delete_patch_note(
    patch_note_id: int = Path(..., description="패치 노트 ID"),
    service: PatchNoteService = Depends(get_service),
):
    """
    패치 노트 삭제

    - ID로 특정 패치 노트 삭제
    """
    try:
        success = await service.delete_patch_note(patch_note_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"패치 노트 ID {patch_note_id}를 찾을 수 없습니다")

        logger.info(f"[PATCHNOTE-API] Deleted patch note ID {patch_note_id}")

        return PatchNoteDeleteResponse(
            success=True,
            message="패치 노트가 삭제되었습니다",
            patch_note_id=patch_note_id,
        )

    except HTTPException:
        raise
    except PatchNoteNotFoundException as e:
        logger.warning(f"[PATCHNOTE-API] Patch note not found: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or "패치 노트를 찾을 수 없습니다")
    except PatchNoteDBConnectionException as e:
        logger.error(f"[PATCHNOTE-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except PatchNoteException as e:
        logger.error(f"[PATCHNOTE-API] Patch note deletion error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "패치 노트 삭제에 실패했습니다")
    except Exception as e:
        logger.error(f"[PATCHNOTE-API] Unexpected error deleting patch note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="패치 노트 삭제 중 예상치 못한 오류가 발생했습니다")
