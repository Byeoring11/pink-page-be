"""
Patch Note Schemas
패치 노트 API 요청/응답 스키마 (Pydantic)
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PatchNoteCreateRequest(BaseModel):
    """패치 노트 생성 요청"""

    title: str = Field(..., min_length=1, max_length=200, description="패치 타이틀")
    content: str = Field(..., min_length=1, description="패치 내용")
    patch_date: date = Field(..., description="패치 날짜 (YYYY-MM-DD)")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """제목 공백 제거"""
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """내용 양쪽 공백 제거"""
        return v.strip()


class PatchNoteUpdateRequest(BaseModel):
    """패치 노트 수정 요청"""

    title: Optional[str] = Field(None, min_length=1, max_length=200, description="패치 타이틀")
    content: Optional[str] = Field(None, min_length=1, description="패치 내용")
    patch_date: Optional[date] = Field(None, description="패치 날짜 (YYYY-MM-DD)")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """제목 공백 제거"""
        return v.strip() if v else None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """내용 양쪽 공백 제거"""
        return v.strip() if v else None


class PatchNoteResponse(BaseModel):
    """패치 노트 응답"""

    id: int
    title: str
    content: str
    patch_date: str  # ISO 8601 format (YYYY-MM-DD)
    created_at: str  # ISO 8601 format
    updated_at: Optional[str] = None  # ISO 8601 format

    model_config = {"from_attributes": True}


class PatchNoteListResponse(BaseModel):
    """패치 노트 목록 응답"""

    total: int = Field(..., description="전체 패치 노트 개수")
    items: list[PatchNoteResponse] = Field(..., description="패치 노트 목록")


class PatchNoteCreateResponse(BaseModel):
    """패치 노트 생성 응답"""

    success: bool
    message: str
    patch_note_id: int


class PatchNoteDeleteResponse(BaseModel):
    """패치 노트 삭제 응답"""

    success: bool
    message: str
    patch_note_id: int
