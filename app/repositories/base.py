from typing import TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete

ModelType = TypeVar("ModelType")


class BaseRepository:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.model = None  # Будет установлено в подклассах

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        async with self.session_factory() as session:
            stmt = select(self.model).where(self.model.id == id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_all(self) -> List[ModelType]:
        async with self.session_factory() as session:
            stmt = select(self.model)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, **kwargs) -> ModelType:
        async with self.session_factory() as session:
            try:
                instance = self.model(**kwargs)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)
                return instance
            except Exception:
                await session.rollback()
                raise

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        async with self.session_factory() as session:
            try:
                stmt = (
                    update(self.model)
                    .where(self.model.id == id)
                    .values(**kwargs)
                    .returning(self.model)
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.scalars().first()
            except Exception:
                await session.rollback()
                raise

    async def delete(self, id: int) -> bool:
        async with self.session_factory() as session:
            try:
                stmt = delete(self.model).where(self.model.id == id)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
            except Exception:
                await session.rollback()
                raise
