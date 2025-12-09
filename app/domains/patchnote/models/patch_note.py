"""
Patch Note Model
패치 노트 데이터 모델 (SQLAlchemy ORM)
"""

from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy import String, Text, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def get_kst_now():
    """한국 시간(KST) 반환"""
    return datetime.now(ZoneInfo("Asia/Seoul"))


class PatchNote(Base):
    """패치 노트 모델"""

    __tablename__ = "patch_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    patch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=get_kst_now, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "patch_date": self.patch_date.isoformat() if self.patch_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<PatchNote(id={self.id}, title='{self.title}', patch_date='{self.patch_date}')>"
