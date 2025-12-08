"""
Stub Load History Schemas
대응답 적재 작업 이력 요청/응답 스키마
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


# ============ Request Schemas ============

class LoadHistoryCreateRequest(BaseModel):
    """작업 이력 생성 요청"""

    batch_id: str = Field(..., description="작업 배치 ID (UUID)")
    customer_numbers: List[str] = Field(..., min_length=1, description="고객번호 목록")
    client_ip: str = Field(..., description="클라이언트 IP 주소")
    connection_id: Optional[str] = Field(None, description="WebSocket 연결 ID")
    execution_time_seconds: float = Field(..., gt=0, description="작업 소요 시간 (초)")
    started_at: datetime = Field(..., description="작업 시작 시간")
    completed_at: datetime = Field(..., description="작업 완료 시간")

    @field_validator("customer_numbers")
    @classmethod
    def validate_customer_numbers(cls, v: List[str]) -> List[str]:
        """고객번호 검증 (9자리 또는 10자리 숫자)"""
        for cusno in v:
            if not cusno.isdigit():
                raise ValueError(f"고객번호는 숫자만 포함해야 합니다: {cusno}")
            if len(cusno) not in [9, 10]:
                raise ValueError(f"고객번호는 9자리 또는 10자리여야 합니다: {cusno}")
        return v

    @field_validator("execution_time_seconds")
    @classmethod
    def validate_execution_time(cls, v: float) -> float:
        """실행 시간 검증 (최대 24시간)"""
        if v > 86400:  # 24시간 = 86400초
            raise ValueError("실행 시간이 24시간을 초과할 수 없습니다")
        return v


class LoadHistoryNoteUpdateRequest(BaseModel):
    """작업 이력 메모 업데이트 요청"""

    note: str = Field(..., max_length=1000, description="작업 이력 메모/설명")


class LoadHistoryQueryParams(BaseModel):
    """작업 이력 조회 쿼리 파라미터"""

    customer_number: Optional[str] = Field(None, description="고객번호로 필터")
    client_ip: Optional[str] = Field(None, description="클라이언트 IP로 필터")
    batch_id: Optional[str] = Field(None, description="배치 ID로 필터")
    limit: int = Field(100, ge=1, le=1000, description="조회 개수 제한")
    offset: int = Field(0, ge=0, description="오프셋")


# ============ Response Schemas ============

class LoadHistoryResponse(BaseModel):
    """작업 이력 단건 응답"""

    id: int
    batch_id: str
    customer_number: str
    client_ip: str
    connection_id: Optional[str]
    execution_time_seconds: float
    started_at: str
    completed_at: str
    created_at: str
    updated_at: Optional[str]
    note: Optional[str]

    class Config:
        from_attributes = True


class LoadHistoryListResponse(BaseModel):
    """작업 이력 목록 응답"""

    total: int = Field(..., description="전체 레코드 수")
    items: List[LoadHistoryResponse] = Field(..., description="작업 이력 목록")


class BatchSummaryResponse(BaseModel):
    """배치 작업 요약 응답"""

    batch_id: str
    total_customers: int
    client_ip: str
    execution_time_seconds: float
    started_at: str
    completed_at: str
    created_at: str


class LoadHistoryCreateResponse(BaseModel):
    """작업 이력 생성 응답"""

    success: bool
    message: str
    batch_id: str
    inserted_count: int


class LoadHistoryNoteUpdateResponse(BaseModel):
    """작업 이력 메모 업데이트 응답"""

    success: bool
    message: str
    history_id: int


class LoadHistoryDeleteResponse(BaseModel):
    """작업 이력 삭제 응답"""

    success: bool
    message: str
    deleted_count: int
    retention_days: int
