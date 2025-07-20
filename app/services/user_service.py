# app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository
from app.models.user import User


class UserService:
    def __init__(self, session_factory: AsyncSession):
        self.session_factory = session_factory

    async def get_or_create_user(
            self,
            user_id: int,
            username: str | None
    ) -> User:
        async with self.session_factory() as session:
            try:
                repository = UserRepository(session)
                
                user = await repository.get_by_telegram_id(user_id)
                
                if user:
                    return user
                
                try:
                    user = await repository.create_from_telegram(
                        telegram_id=user_id,
                        username=username
                    )
                except Exception:
                    raise
                
                return user
            except Exception:
                raise

    async def get_user(self, user_id: int) -> User | None:
        async with self.session_factory() as session:
            repository = UserRepository(session)
            return await repository.get_by_telegram_id(user_id)
