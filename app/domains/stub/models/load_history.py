"""
Stub Load History Model
대응답 적재 작업 이력 DB 모델 (SQLAlchemy ORM)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StubLoadHistory(Base):
    """대응답 적재 작업 이력 테이블"""

    __tablename__ = "stub_load_history"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 작업 정보
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # 클라이언트 정보
    client_ip: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    connection_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 작업 시간 정보
    execution_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 제약 조건
    __table_args__ = (
        UniqueConstraint('batch_id', 'customer_number', name='uq_batch_customer'),
        Index('idx_stub_load_history_created_at_desc', 'created_at', postgresql_using='btree'),
        Index('idx_stub_load_history_completed_at_desc', 'completed_at', postgresql_using='btree'),
    )

    def to_dict(self) -> dict:
        """모델을 딕셔너리로 변환 (API 응답용)"""
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "customer_number": self.customer_number,
            "client_ip": self.client_ip,
            "connection_id": self.connection_id,
            "execution_time_seconds": self.execution_time_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "note": self.note,
        }
