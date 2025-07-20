# app/bot/middlewares/auth.py
from typing import Dict, Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.core.logging import logger


class AuthMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        try:
            # Get user service from data
            user_service: UserService = data.get('user_service')
            if not user_service:
                return await handler(event, data)
            
            # Extract user from different event types
            user = None
            
            if event.message:
                user = event.message.from_user
            elif event.callback_query:
                user = event.callback_query.from_user
            elif hasattr(event, 'from_user') and event.from_user:
                user = event.from_user
            
            if not user:
                return await handler(event, data)
            
            # Check and register user if needed
            try:
                telegram_user = await user_service.get_or_create_user(
                    user_id=user.id,
                    username=user.username
                )
                
                # Add user to data dict for handlers
                data['user'] = telegram_user
                
            except Exception:
                pass
            
            return await handler(event, data)
            
        except Exception:
            # Не пытаемся отправить сообщение, так как не знаем, как ответить на Update
            return await handler(event, data)
