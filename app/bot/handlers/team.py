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
            # Replace message.get_args() with parsing the message text
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)
            
            # Check if there are arguments after the command
            if len(parts) < 2:
                await message.reply(
                    "Please specify a team name: /create_team Team_name")
                return
            
            # Get the team name (everything after the first space)
            team_name = parts[1].strip()
            
            success, result_message = await self.team_service.create_team(
                telegram_id=message.from_user.id,
                team_name=team_name
            )

            if success:
                # If the team is successfully created, send a message with the full keyboard
                await message.reply(
                    result_message + "\n\nNow all bot functions are available to you!",
                    reply_markup=get_full_keyboard()
                )
            else:
                # If an error occurred, just send the error message
                await message.reply(result_message)
                
            logger.info(f"User {message.from_user.id} attempted to create team '{team_name}': {success}")

        except Exception as e:
            logger.error(f"Error creating team: {e}", exc_info=True)
            await message.reply("An error occurred while creating the team")

    async def cmd_invite(self, message: types.Message):
        try:
            # Сначала проверяем, является ли пользователь администратором команды
            team = await self.team_service.get_user_team(message.from_user.id)
            if not team:
                await message.reply("You are not a member of any team")
                return
                
            is_admin = await self.team_service.is_team_admin(
                message.from_user.id, team.id)
            
            if not is_admin:
                await message.reply("This command is only available to team administrators")
                logger.info(f"Non-admin user {message.from_user.id} attempted to use invite command")
                return
            
            # Если пользователь администратор, продолжаем обработку команды
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
            logger.info(f"Admin user {message.from_user.id} attempted to invite {username}: {success}")

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
            
            admin_commands = ""
            if is_admin:
                admin_commands = (
                    "\n\nAdmin commands:"
                    "\n/invite @username - invite a member by username"
                    "\n/create_invite [days] - create an invite code (default 7 days)"
                )
            
            await message.reply(
                f"🏢 Team Information:\n\n"
                f"Name: {team.name}\n"
                f"Team ID: {team.id}\n"
                f"{admin_status}{admin_commands}\n\n"
                f"Use /leave_team to leave this team."
            )
            
        except Exception as e:
            logger.error(f"Error getting team info: {e}", exc_info=True)
            await message.reply("An error occurred while retrieving team information")

    async def cmd_create_invite(self, message: types.Message):
        """Handler for /create_invite command"""
        try:
            # Проверяем, является ли пользователь администратором команды
            team = await self.team_service.get_user_team(message.from_user.id)
            if not team:
                await message.reply("You are not a member of any team")
                return
                
            is_admin = await self.team_service.is_team_admin(
                message.from_user.id, team.id)
            
            if not is_admin:
                await message.reply("This command is only available to team administrators")
                logger.info(f"Non-admin user {message.from_user.id} attempted to use create_invite command")
                return
                
            # Parse command arguments for expiration days (optional)
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)
            
            expires_in_days = 7  # Default expiration
            
            if len(parts) > 1:
                try:
                    expires_in_days = int(parts[1].strip())
                    if expires_in_days < 1 or expires_in_days > 30:
                        await message.reply(
                            "Expiration period must be between 1 and 30 days. Default value (7 days) will be used.")
                        expires_in_days = 7
                except ValueError:
                    await message.reply(
                        "Invalid expiration period format. Default value (7 days) will be used.")
            
            success, result_message = await self.team_service.create_invite_link(
                admin_telegram_id=message.from_user.id,
                expires_in_days=expires_in_days
            )
            
            result_message = result_message.replace("`", "")
            await message.reply(result_message)
            logger.info(f"User {message.from_user.id} created invite: {success}")
            
        except Exception as e:
            logger.error(f"Error creating invite: {e}", exc_info=True)
            await message.reply("An error occurred while creating the invite code")

    async def cmd_join_team(self, message: types.Message):
        """Handler for /join_team command"""
        try:
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)
            
            if len(parts) < 2:
                await message.reply(
                    "Please specify the invite code: /join_team INVITE_CODE")
                return
            
            invite_code = parts[1].strip()
            
            success, result_message = await self.team_service.join_team_by_code(
                telegram_id=message.from_user.id,
                invite_code=invite_code
            )
            
            if success:
                await message.reply(
                    result_message + "\n\nNow all bot functions are available to you!",
                    reply_markup=get_full_keyboard()
                )
            else:
                await message.reply(result_message)
                
            logger.info(f"User {message.from_user.id} joined team with code {invite_code}: {success}")
            
        except Exception as e:
            logger.error(f"Error joining team: {e}", exc_info=True)
            await message.reply("An error occurred while joining the team")
    
    async def cmd_leave_team(self, message: types.Message):
        """Handler for /leave_team command"""
        try:
            success, result_message = await self.team_service.leave_team(
                telegram_id=message.from_user.id
            )
            
            if success:
                # Если пользователь успешно вышел из команды, возвращаем начальную клавиатуру
                from app.bot.handlers.base import get_initial_keyboard
                await message.reply(
                    result_message + "\n\nYou have left your team. Some functions are now unavailable.",
                    reply_markup=get_initial_keyboard()
                )
            else:
                await message.reply(result_message)
                
            logger.info(f"User {message.from_user.id} attempted to leave team: {success}")
            
        except Exception as e:
            logger.error(f"Error leaving team: {e}", exc_info=True)
            await message.reply("An error occurred while leaving the team")

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
    router.message.register(
        handlers.cmd_create_invite,
        Command("create_invite")
    )
    router.message.register(
        handlers.cmd_join_team,
        Command("join_team")
    )
    router.message.register(
        handlers.cmd_leave_team,
        Command("leave_team")
    )
    return router 
