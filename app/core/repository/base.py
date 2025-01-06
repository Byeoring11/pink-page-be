from typing import TypeVar, Type, Optional, Generic, Any, Tuple

from sqlalchemy import func, select, update, delete

from core.db import Base, session
from core.repository.enum import SynchronizeSessionEnum

ModelType = TypeVar("ModelType", bound=Base)
ModelIdType = TypeVar("ModelIdType", bound=Tuple[Any, ...])


class CRUDRepository(Generic[ModelType, ModelIdType]):
    def __init__(self, model: Type[ModelType], pk_columns: Tuple[str]):
        self.model = model
        self.attr_names = self.model.__table__.columns.keys()
        self.pk_columns = pk_columns

    async def total(self, **params):
        filters = [
            getattr(self.model, key) == value
            for key, value in params.items()
        ]
        query = select(func.count()).where(*filters)
        result = await session.execute(query)
        return result.scalar()

    async def all_by_filter(self, **params):
        query = select(self.model).filter_by(**params)
        result = await session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, ids: ModelIdType) -> Optional[ModelType]:
        filters = [
            getattr(self.model, pk) == value
            for pk, value in zip(self.pk_columns, ids)
        ]
        query = select(self.model).where(*filters)
        result = await session.execute(query)
        return result.scalars().first()

    async def get_by_filter(self, **params) -> Optional[ModelType]:
        query = select(self.model).filter_by(**params)
        result = await session.execute(query)
        return result.scalars().first()

    async def update_by_id(
            self,
            ids: ModelIdType,
            params: dict,
            synchronize_session: SynchronizeSessionEnum = SynchronizeSessionEnum.EVALUATE,
    ) -> None:
        filters = [
            getattr(self.model, pk) == value
            for pk, value in zip(self.pk_columns, ids)
        ]
        query = (
            update(self.model)
            .where(*filters)
            .values(**params)
            .execution_options(synchronize_session=synchronize_session.value)
        )
        await session.execute(query)

    async def update_by_filter(
            self,
            filter_params: dict,
            value_params: dict,
            synchronize_session: SynchronizeSessionEnum =  SynchronizeSessionEnum.EVALUATE,
    ) -> None:
        filters = [
            getattr(self.model, key) == value
            for key, value in filter_params.items()
        ]
        query = (
            update(self.model)
            .where(*filters)
            .values(**value_params)
            .execution_options(synchronize_session=synchronize_session.value)
        )
        await session.execute(query)

    async def delete(self, model: ModelType) -> None:
        await session.delete(model)

    async def delete_by_id(
            self,
            ids: ModelIdType,
            synchronize_session: SynchronizeSessionEnum = SynchronizeSessionEnum.FETCH,
    ) -> None:
        filters = [
            getattr(self.model, pk) == value
            for pk, value in zip(self.pk_columns, ids)
        ]
        query = (
            delete(self.model)
            .where(*filters)
            .execution_options(synchronize_session=synchronize_session.value)
        )
        await session.execute(query)

    async def delete_by_filter(
            self,
            filter_params: dict,
            synchronize_session: SynchronizeSessionEnum = SynchronizeSessionEnum.FETCH,
    ) -> None:
        filters = [
            getattr(self.model, key) == value
            for key, value in filter_params.items()
        ]
        query = (
            delete(self.model)
            .where(*filters)
            .execution_options(synchronize_session=synchronize_session.value)
        )
        await session.execute(query)

    async def save(self, model: ModelType) -> ModelType:
        session.add(model)
        await session.flush()
        await session.refresh(model)
        return model
