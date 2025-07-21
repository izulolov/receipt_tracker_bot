# app/services/user_service.py
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.repositories.user import UserRepository
from app.models.user import User


class UserService:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.repository = UserRepository(session_factory)  # Создаем репозиторий один раз

    async def get_or_create_user(
            self,
            user_id: int,
            username: str | None
    ) -> User:
        # Используем уже созданный репозиторий
        user = await self.repository.get_by_telegram_id(user_id)
        
        if not user:
            # Если пользователя нет, создаем его
            user = await self.repository.create_from_telegram(
                telegram_id=user_id,
                username=username or ""
            )
        
        return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.repository.get_by_telegram_id(telegram_id)
    
    async def get_all_users(self) -> list[User]:
        return await self.repository.get_all()
    
    async def update_user(self, user_id: int, **kwargs) -> User:
        return await self.repository.update(user_id, **kwargs)
    
    async def delete_user(self, user_id: int) -> None:
        await self.repository.delete(user_id)
