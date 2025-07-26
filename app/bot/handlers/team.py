# app/bot/handlers/team.py
import logging
from aiogram import Router, types
from aiogram.filters import Command

from app.services.team_service import TeamService
from app.bot.handlers.base import get_full_keyboard

from app.core.logging import logger


class TeamHandlers:
    def __init__(self, team_service: TeamService):
        self.team_service = team_service

    async def cmd_create_team(self, message: types.Message):
        try:
            # Заменяем message.get_args() на парсинг текста сообщения
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)
            
            # Проверяем, есть ли аргументы после команды
            if len(parts) < 2:
                await message.reply(
                    "Please specify a team name: /create_team Team_name")
                return
            
            # Получаем название команды (все, что после первого пробела)
            team_name = parts[1].strip()
            
            success, result_message = await self.team_service.create_team(
                telegram_id=message.from_user.id,
                team_name=team_name
            )

            if success:
                # Если команда успешно создана, отправляем сообщение с полной клавиатурой
                await message.reply(
                    result_message + "\n\nNow all bot functions are available to you!",
                    reply_markup=get_full_keyboard()
                )
            else:
                # Если произошла ошибка, просто отправляем сообщение об ошибке
                await message.reply(result_message)
                
            logger.info(f"User {message.from_user.id} attempted to create team '{team_name}': {success}")

        except Exception as e:
            logger.error(f"Error creating team: {e}", exc_info=True)
            await message.reply("An error occurred while creating the team")

    async def cmd_invite(self, message: types.Message):
        try:
            # Аналогично исправляем парсинг для команды invite
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)
            
            if len(parts) < 2:
                await message.reply(
                    "Please specify a username: /invite @username")
                return

            username = parts[1].lstrip('@')
            success, result_message = await self.team_service.invite_member(
                admin_telegram_id=message.from_user.id,
                username=username
            )

            await message.reply(result_message)
            logger.info(f"User {message.from_user.id} attempted to invite {username}: {success}")

        except Exception as e:
            logger.error(f"Error inviting user: {e}", exc_info=True)
            await message.reply("An error occurred while inviting the user")

    async def cmd_team_info(self, message: types.Message):
        try:
            team = await self.team_service.get_user_team(message.from_user.id)
            if not team:
                await message.reply("You are not a member of any team")
                return
                
            is_admin = await self.team_service.is_team_admin(
                message.from_user.id, team.id)
            
            admin_status = "✅ You are the administrator of this team" if is_admin else ""
            
            await message.reply(
                f"🏢 Team Information:\n\n"
                f"Name: {team.name}\n"
                f"Team ID: {team.id}\n"
                f"{admin_status}\n\n"
                f"Use /invite @username to invite a member"
            )
            
        except Exception as e:
            logger.error(f"Error getting team info: {e}", exc_info=True)
            await message.reply("An error occurred while retrieving team information")


def setup_team_handlers(team_service: TeamService) -> Router:
    router = Router()
    handlers = TeamHandlers(team_service)

    router.message.register(
        handlers.cmd_create_team,
        Command("create_team")
    )
    router.message.register(
        handlers.cmd_invite,
        Command("invite")
    )
    router.message.register(
        handlers.cmd_team_info,
        Command("team_info")
    )

    return router
