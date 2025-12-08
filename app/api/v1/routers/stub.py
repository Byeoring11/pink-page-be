"""
Stub Load History REST API Router
대응답 적재 작업 이력 REST API 엔드포인트
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query, Path
from typing import Optional

from app.core.logger import logger
from app.core.exceptions.base import (
    StubLoadHistoryException,
    StubLoadHistoryBatchNotFoundException,
    StubLoadHistoryDuplicateException,
    StubLoadHistoryValidationException,
    StubLoadHistoryDBConnectionException,
)
from app.domains.stub.schemas.load_history_schemas import (
    LoadHistoryCreateRequest,
    LoadHistoryCreateResponse,
    LoadHistoryResponse,
    LoadHistoryListResponse,
    BatchSummaryResponse,
    LoadHistoryNoteUpdateRequest,
    LoadHistoryNoteUpdateResponse,
    LoadHistoryDeleteResponse,
)
from app.domains.stub.services.load_history_service import StubLoadHistoryService

router = APIRouter(prefix="/stub", tags=["Stub"])

# Service 싱글톤
_service: Optional[StubLoadHistoryService] = None


def get_service() -> StubLoadHistoryService:
    """서비스 의존성 주입"""
    global _service
    if _service is None:
        _service = StubLoadHistoryService()
    return _service


@router.post("/histories", response_model=LoadHistoryCreateResponse, status_code=201)
async def create_histories(
    request_body: LoadHistoryCreateRequest,
    http_request: Request,
    service: StubLoadHistoryService = Depends(get_service),
):
    """
    작업 이력 생성

    - 고객번호 단위로 여러 row 적재
    - 10개 고객번호 입력 시 → 10개 레코드 생성
    - 클라이언트 IP는 자동으로 추출됨
    """
    try:
        # 클라이언트 IP 자동 추출
        if not request_body.client_ip or request_body.client_ip == "unknown":
            client_ip = http_request.client.host if http_request.client else "unknown"
            request_body.client_ip = client_ip

        inserted_count = await service.create_histories(request_body)

        logger.info(
            f"[STUB-API] Created {inserted_count} histories for batch {request_body.batch_id} "
            f"from {request_body.client_ip}"
        )

        return LoadHistoryCreateResponse(
            success=True,
            message=f"작업 이력이 저장되었습니다 ({inserted_count}건)",
            batch_id=request_body.batch_id,
            inserted_count=inserted_count,
        )

    except StubLoadHistoryValidationException as e:
        logger.warning(f"[STUB-API] Validation error: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or str(e))
    except StubLoadHistoryDuplicateException as e:
        logger.warning(f"[STUB-API] Duplicate entry: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or "중복된 작업 이력이 존재합니다")
    except StubLoadHistoryDBConnectionException as e:
        logger.error(f"[STUB-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except StubLoadHistoryException as e:
        logger.error(f"[STUB-API] Load history error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "작업 이력 저장에 실패했습니다")
    except Exception as e:
        logger.error(f"[STUB-API] Unexpected error creating histories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="작업 이력 저장 중 예상치 못한 오류가 발생했습니다")


@router.get("/histories", response_model=LoadHistoryListResponse)
async def get_histories(
    customer_number: Optional[str] = Query(None, description="고객번호로 필터"),
    client_ip: Optional[str] = Query(None, description="클라이언트 IP로 필터"),
    batch_id: Optional[str] = Query(None, description="배치 ID로 필터"),
    limit: int = Query(100, ge=1, le=1000, description="조회 개수 제한"),
    offset: int = Query(0, ge=0, description="오프셋"),
    service: StubLoadHistoryService = Depends(get_service),
):
    """
    작업 이력 목록 조회

    - 필터 없이 조회 시: 최근 100건 반환
    - 고객번호, IP, 배치 ID로 필터링 가능
    - 페이징 지원 (limit/offset)
    """
    try:
        result = await service.get_histories(
            customer_number=customer_number,
            client_ip=client_ip,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )

        logger.info(f"[STUB-API] Retrieved {len(result.items)} histories (total: {result.total})")
        return result

    except StubLoadHistoryDBConnectionException as e:
        logger.error(f"[STUB-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except StubLoadHistoryException as e:
        logger.error(f"[STUB-API] Load history query error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "작업 이력 조회에 실패했습니다")
    except Exception as e:
        logger.error(f"[STUB-API] Unexpected error getting histories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="작업 이력 조회 중 예상치 못한 오류가 발생했습니다")


@router.get("/histories/{history_id}", response_model=LoadHistoryResponse)
async def get_history_by_id(
    history_id: int = Path(..., description="이력 ID"),
    service: StubLoadHistoryService = Depends(get_service),
):
    """
    단일 작업 이력 조회

    - ID로 특정 이력 조회
    """
    try:
        history = await service.get_history_by_id(history_id)

        if not history:
            raise HTTPException(status_code=404, detail=f"이력 ID {history_id}를 찾을 수 없습니다")

        logger.info(f"[STUB-API] Retrieved history ID {history_id}")
        return history

    except HTTPException:
        raise
    except StubLoadHistoryDBConnectionException as e:
        logger.error(f"[STUB-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except StubLoadHistoryException as e:
        logger.error(f"[STUB-API] Load history query error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "작업 이력 조회에 실패했습니다")
    except Exception as e:
        logger.error(f"[STUB-API] Unexpected error getting history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="작업 이력 조회 중 예상치 못한 오류가 발생했습니다")


@router.patch("/histories/{history_id}/note", response_model=LoadHistoryNoteUpdateResponse)
async def update_history_note(
    history_id: int = Path(..., description="이력 ID"),
    request_body: LoadHistoryNoteUpdateRequest = ...,
    service: StubLoadHistoryService = Depends(get_service),
):
    """
    작업 이력 메모 업데이트

    - 특정 이력에 메모/설명 추가 또는 수정
    - 최대 1000자까지 입력 가능
    """
    try:
        success = await service.update_note(history_id, request_body)

        if not success:
            raise HTTPException(status_code=404, detail=f"이력 ID {history_id}를 찾을 수 없습니다")

        logger.info(f"[STUB-API] Updated note for history ID {history_id}")

        return LoadHistoryNoteUpdateResponse(
            success=True,
            message="메모가 업데이트되었습니다",
            history_id=history_id,
        )

    except HTTPException:
        raise
    except StubLoadHistoryDBConnectionException as e:
        logger.error(f"[STUB-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except StubLoadHistoryException as e:
        logger.error(f"[STUB-API] Load history update error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "메모 업데이트에 실패했습니다")
    except Exception as e:
        logger.error(f"[STUB-API] Unexpected error updating note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="메모 업데이트 중 예상치 못한 오류가 발생했습니다")


@router.get("/batches/{batch_id}", response_model=BatchSummaryResponse)
async def get_batch_summary(
    batch_id: str = Path(..., description="배치 ID"),
    service: StubLoadHistoryService = Depends(get_service),
):
    """
    배치 작업 요약 조회

    - 배치 ID로 전체 작업 요약 정보 반환
    - 총 고객번호 수, 실행 시간 등
    """
    try:
        summary = await service.get_batch_summary(batch_id)

        logger.info(f"[STUB-API] Retrieved batch summary for {batch_id}")
        return summary

    except StubLoadHistoryBatchNotFoundException as e:
        logger.warning(f"[STUB-API] Batch not found: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or "배치 ID를 찾을 수 없습니다")
    except StubLoadHistoryDBConnectionException as e:
        logger.error(f"[STUB-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except StubLoadHistoryException as e:
        logger.error(f"[STUB-API] Load history query error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "배치 요약 조회에 실패했습니다")
    except Exception as e:
        logger.error(f"[STUB-API] Unexpected error getting batch summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="배치 요약 조회 중 예상치 못한 오류가 발생했습니다")


@router.get("/customers/{customer_number}/histories", response_model=list[LoadHistoryResponse])
async def get_customer_histories(
    customer_number: str = Path(..., description="고객번호"),
    limit: int = Query(10, ge=1, le=100, description="조회 개수 제한"),
    service: StubLoadHistoryService = Depends(get_service),
):
    """
    특정 고객번호의 작업 이력 조회

    - 해당 고객번호가 포함된 모든 작업 이력 반환
    - 최근순으로 정렬
    """
    try:
        histories = await service.get_customer_histories(customer_number, limit)

        logger.info(f"[STUB-API] Retrieved {len(histories)} histories for customer {customer_number}")
        return histories

    except StubLoadHistoryDBConnectionException as e:
        logger.error(f"[STUB-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except StubLoadHistoryException as e:
        logger.error(f"[STUB-API] Load history query error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "고객 이력 조회에 실패했습니다")
    except Exception as e:
        logger.error(f"[STUB-API] Unexpected error getting customer histories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="고객 이력 조회 중 예상치 못한 오류가 발생했습니다")


@router.delete("/histories", response_model=LoadHistoryDeleteResponse)
async def delete_old_histories(
    days: int = Query(90, ge=30, le=365, description="보관 일수"),
    service: StubLoadHistoryService = Depends(get_service),
):
    """
    오래된 작업 이력 삭제

    - 지정한 일수보다 오래된 레코드 삭제
    - 기본값: 90일
    - 범위: 30일 ~ 365일
    """
    try:
        deleted_count = await service.delete_old_histories(days)

        logger.info(f"[STUB-API] Deleted {deleted_count} old histories (>{days} days)")

        return LoadHistoryDeleteResponse(
            success=True,
            message=f"{deleted_count}건의 오래된 이력이 삭제되었습니다",
            deleted_count=deleted_count,
            retention_days=days,
        )

    except StubLoadHistoryValidationException as e:
        logger.warning(f"[STUB-API] Validation error: {e}")
        raise HTTPException(status_code=e.http_status, detail=e.detail or "유효하지 않은 보관 일수입니다")
    except StubLoadHistoryDBConnectionException as e:
        logger.error(f"[STUB-API] Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail="데이터베이스 연결에 실패했습니다")
    except StubLoadHistoryException as e:
        logger.error(f"[STUB-API] Load history deletion error: {e}", exc_info=True)
        raise HTTPException(status_code=e.http_status, detail=e.detail or "이력 정리에 실패했습니다")
    except Exception as e:
        logger.error(f"[STUB-API] Unexpected error deleting histories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="이력 정리 중 예상치 못한 오류가 발생했습니다")
