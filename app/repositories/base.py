from typing import TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

ModelType = TypeVar("ModelType")


class BaseRepository:
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self) -> List[ModelType]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs) -> ModelType:
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            
            try:
                await self.session.commit()
            except Exception:
                raise
            
            try:
                await self.session.refresh(instance)
            except Exception:
                raise
            
            return instance
        except Exception:
            raise

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalars().first()

    async def delete(self, id: int) -> bool:
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
