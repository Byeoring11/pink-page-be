from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from pydantic import BaseModel
from sqlalchemy import Select, select, update, and_
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError

from app.core.logger import logger
from app.db.base import Base
from app.db.session import session

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        Repository 생성자
        :param model: SQLAlchemy 모델 클래스
        """
        self.model = model

    async def get_by(
        self,
        *,
        filters: Optional[dict] = None,
        filter_expressions: Optional[list] = None,
        options: Optional[list] = None,
        unique: bool = True
    ) -> Optional[ModelType]:
        """
        조건 기반 단일 객체 조회

        :param filters: {컬럼명: 값} 형태의 딕셔너리 필터
        :param filter_expressions: SQLAlchemy 표현식 리스트
        :param options: 관계 로딩 옵션 (예: joinedload)
        :param unique: 단일 결과 보장 여부
        """
        try:
            query = select(self.model)

            # 필터 조건 적용
            if filters:
                query = self._apply_filters(query, filters)
            if filter_expressions:
                query = query.where(and_(*filter_expressions))

            # 관계 로딩 옵션
            if options:
                for option in options:
                    query = query.options(option)

            result = await session.execute(query)

            return result.scalar_one_or_none() if unique else result.scalars().first()

        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__}: {str(e)}")
            raise

    def _apply_filters(self, query: Select, filters: dict) -> Select:
        """딕셔너리 필터를 SQLAlchemy 조건으로 변환"""
        conditions = []
        for key, value in filters.items():
            if "__" in key:
                # 관계 필드 필터링 지원 (예: user__email)
                relationship, field = key.split("__", 1)
                conditions.append(getattr(getattr(self.model, relationship), field) == value)
            else:
                conditions.append(getattr(self.model, key) == value)
        return query.where(and_(*conditions))

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Dict[str, Any] = None
    ) -> List[ModelType]:
        """
        여러 객체 조회 (페이지네이션 및 필터링 지원)
        """
        try:
            query = select(self.model)

            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)

            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {str(e)}")
            raise

    async def save(self, *, obj_in: CreateSchemaType) -> ModelType:
        """
        새 객체 생성
        """
        try:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)
            session.add(db_obj)
            await session.flush()
            await session.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise

    async def update_one(
        self,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """
        객체 업데이트
        """
        try:
            obj_data = jsonable_encoder(db_obj)

            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True)

            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])

            session.add(db_obj)
            await session.flush()
            await session.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__}: {str(e)}")
            raise

    async def update_multi(
        self,
        *,
        filters: Optional[dict] = None,
        filter_expressions: Optional[list] = None,
        update_values: Dict[str, Any]
    ) -> int:
        """
        여러 객체 업데이트
        """
        try:
            query = update(self.model)

            # 필터 조건 적용
            if filters:
                query = self._apply_filters(query, filters)
            if filter_expressions:
                query = query.where(and_(*filter_expressions))

            query = query.values(**update_values)

            result = await session.execute(query)
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Error bulk updating {self.model.__name__}: {str(e)}")
            raise

    async def delete_by(
        self,
        *,
        filters: Optional[dict] = None,
        filter_expressions: Optional[list] = None,
    ) -> ModelType:
        """
        객체 삭제
        """
        try:
            obj = await self.get_by(filters=filters, filter_expressions=filter_expressions)
            if obj:
                await session.delete(obj)
                await session.commit()
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {str(e)}")
            raise
