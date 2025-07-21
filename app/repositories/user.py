from typing import Optional
from sqlalchemy import select
from app.models.user import User
from .base import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.model = User

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        async with self.session_factory() as session:
            try:
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                user = result.scalars().first()
                return user
            except Exception:
                raise

    async def get_by_username(self, username: str) -> Optional[User]:
        async with self.session_factory() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def create_from_telegram(
            self,
            telegram_id: int,
            username: str
    ) -> User:
        try:
            user = await self.create(
                telegram_id=telegram_id,
                username=username
            )
            return user
        except Exception:
            raise
