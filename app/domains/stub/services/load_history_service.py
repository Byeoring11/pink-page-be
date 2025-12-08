"""
Stub Load History Service
대응답 적재 작업 이력 비즈니스 로직 레이어
"""

from typing import List, Optional

from app.core.logger import logger
from app.core.exceptions.base import (
    StubLoadHistoryBatchNotFoundException,
    StubLoadHistoryValidationException,
)
from app.domains.stub.repositories.load_history_repository import StubLoadHistoryRepository
from app.domains.stub.models.load_history import StubLoadHistory
from app.domains.stub.schemas.load_history_schemas import (
    LoadHistoryCreateRequest,
    LoadHistoryResponse,
    LoadHistoryListResponse,
    BatchSummaryResponse,
    LoadHistoryNoteUpdateRequest,
)


class StubLoadHistoryService:
    """대응답 적재 작업 이력 서비스"""

    def __init__(self, repository: Optional[StubLoadHistoryRepository] = None):
        """
        Args:
            repository: Repository 인스턴스 (의존성 주입)
        """
        self.repository = repository or StubLoadHistoryRepository()

    async def initialize(self) -> None:
        """서비스 초기화 (DB 초기화)"""
        await self.repository.initialize_db()

    async def create_histories(self, request: LoadHistoryCreateRequest) -> int:
        """
        작업 이력 생성 (고객번호별 레코드 생성)

        Args:
            request: 작업 이력 생성 요청

        Returns:
            생성된 레코드 수
        """
        # 요청을 모델로 변환 (SQLAlchemy 모델)
        histories = []
        for customer_number in request.customer_numbers:
            history = StubLoadHistory(
                batch_id=request.batch_id,
                customer_number=customer_number,
                client_ip=request.client_ip,
                connection_id=request.connection_id,
                execution_time_seconds=request.execution_time_seconds,
                started_at=request.started_at,  # datetime 객체 직접 전달
                completed_at=request.completed_at,  # datetime 객체 직접 전달
            )
            histories.append(history)

        # Repository를 통해 저장
        inserted_count = await self.repository.create_bulk(histories)
        logger.info(
            f"[LoadHistoryService] Created {inserted_count} histories for batch {request.batch_id}"
        )
        return inserted_count

    async def get_history_by_id(self, history_id: int) -> Optional[LoadHistoryResponse]:
        """
        ID로 단일 이력 조회

        Args:
            history_id: 이력 ID

        Returns:
            작업 이력 또는 None
        """
        history = await self.repository.find_by_id(history_id)
        if history:
            return LoadHistoryResponse(**history.to_dict())
        return None

    async def get_histories(
        self,
        customer_number: Optional[str] = None,
        client_ip: Optional[str] = None,
        note: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> LoadHistoryListResponse:
        """
        작업 이력 목록 조회

        Args:
            customer_number: 고객번호 필터
            client_ip: IP 필터
            note: Note 내용 필터
            limit: 조회 개수
            offset: 오프셋

        Returns:
            작업 이력 목록 및 전체 개수
        """
        histories, total = await self.repository.find_all(
            customer_number=customer_number,
            client_ip=client_ip,
            note=note,
            limit=limit,
            offset=offset,
        )

        items = [LoadHistoryResponse(**h.to_dict()) for h in histories]
        logger.info(f"[LoadHistoryService] Retrieved {len(items)} histories (total: {total})")

        return LoadHistoryListResponse(total=total, items=items)

    async def get_batch_summary(self, batch_id: str) -> BatchSummaryResponse:
        """
        배치 작업 요약 조회

        Args:
            batch_id: 배치 ID

        Returns:
            배치 작업 요약

        Raises:
            StubLoadHistoryBatchNotFoundException: 배치를 찾을 수 없음
        """
        histories = await self.repository.find_by_batch_id(batch_id)

        if not histories:
            raise StubLoadHistoryBatchNotFoundException(batch_id=batch_id)

        # 첫 번째 레코드에서 공통 정보 추출
        first = histories[0]

        return BatchSummaryResponse(
            batch_id=batch_id,
            total_customers=len(histories),
            client_ip=first.client_ip,
            execution_time_seconds=first.execution_time_seconds,
            started_at=first.started_at.isoformat() if first.started_at else "",
            completed_at=first.completed_at.isoformat() if first.completed_at else "",
            created_at=first.created_at.isoformat() if first.created_at else "",
        )

    async def get_customer_histories(
        self, customer_number: str, limit: int = 10
    ) -> List[LoadHistoryResponse]:
        """
        특정 고객번호의 작업 이력 조회

        Args:
            customer_number: 고객번호
            limit: 조회 개수

        Returns:
            작업 이력 목록
        """
        histories = await self.repository.find_by_customer_number(customer_number, limit)
        logger.info(f"[LoadHistoryService] Retrieved {len(histories)} histories for customer {customer_number}")

        return [LoadHistoryResponse(**h.to_dict()) for h in histories]

    async def update_note(self, history_id: int, request: LoadHistoryNoteUpdateRequest) -> bool:
        """
        작업 이력 메모 업데이트

        Args:
            history_id: 이력 ID
            request: 메모 업데이트 요청

        Returns:
            업데이트 성공 여부
        """
        # 이력 존재 확인
        history = await self.repository.find_by_id(history_id)
        if not history:
            return False

        # 메모 업데이트
        success = await self.repository.update_note(history_id, request.note)
        if success:
            logger.info(f"[LoadHistoryService] Updated note for history ID {history_id}")

        return success

    async def delete_old_histories(self, days: int = 90) -> int:
        """
        오래된 작업 이력 삭제

        Args:
            days: 보관 일수

        Returns:
            삭제된 레코드 수
        """
        # 유효성 검증
        if days < 30 or days > 365:
            raise StubLoadHistoryValidationException(
                field="days",
                value=days,
                detail="보관 일수는 30일에서 365일 사이여야 합니다"
            )

        deleted_count = await self.repository.delete_older_than(days)
        logger.info(f"[LoadHistoryService] Deleted {deleted_count} old histories (>{days} days)")

        return deleted_count
