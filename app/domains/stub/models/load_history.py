"""
Stub Load History Model
대응답 적재 작업 이력 DB 모델
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StubLoadHistory:
    """대응답 적재 작업 이력 엔티티"""

    # Primary Key
    id: Optional[int] = None

    # 작업 정보
    batch_id: str = ""
    customer_number: str = ""

    # 클라이언트 정보
    client_ip: str = ""
    connection_id: Optional[str] = None

    # 작업 시간 정보
    execution_time_seconds: float = 0.0
    started_at: str = ""  # ISO 8601 format
    completed_at: str = ""  # ISO 8601 format

    # 메타데이터
    created_at: str = ""  # ISO 8601 format
    updated_at: Optional[str] = None  # ISO 8601 format
    note: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: dict) -> "StubLoadHistory":
        """데이터베이스 row에서 모델 생성"""
        return cls(
            id=row.get("id"),
            batch_id=row.get("batch_id", ""),
            customer_number=row.get("customer_number", ""),
            client_ip=row.get("client_ip", ""),
            connection_id=row.get("connection_id"),
            execution_time_seconds=row.get("execution_time_seconds", 0.0),
            started_at=row.get("started_at", ""),
            completed_at=row.get("completed_at", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at"),
            note=row.get("note"),
        )

    def to_dict(self) -> dict:
        """모델을 딕셔너리로 변환"""
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "customer_number": self.customer_number,
            "client_ip": self.client_ip,
            "connection_id": self.connection_id,
            "execution_time_seconds": self.execution_time_seconds,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "note": self.note,
        }
