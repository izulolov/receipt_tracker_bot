# app/bot/handlers/team.py
import random
import string
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.services.team_service import TeamService
from app.bot.handlers.base import get_full_keyboard
from app.core.logging import logger

# Добавим класс состояний для выхода из команды
class LeaveTeamStates(StatesGroup):
    waiting_for_confirmation = State()

# Добавим функцию для генерации случайного кода
def generate_confirmation_code(length=6):
    """Generate a random confirmation code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

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
            
            # Получаем количество участников команды
            member_count = await self.team_service.get_team_member_count(team.id)
            
            admin_status = "✅ You are the administrator of this team" if is_admin else ""
            
            admin_commands = ""
            if is_admin:
                admin_commands = (
                    "\n\nAdmin commands:\n"
                    "/create_invite [days] - create an invite code (default 7 days). "
                    "If you simply send /create_invite to the bot, a code will be created that is valid for 7 days. "
                    "You can also specify how many days the team connection code will be valid for.\n\n"
                    "/join_team [code] - this is how a user can join a team by entering the command /join_team xxxxxxxx "
                    "in their bot, where xxxxxxxx is the code generated in the \"/create_invite [days]\" step.\n\n"
                    "/invite @username - Another way to add a user is by using @username. "
                    "The user must start the bot, after which the administrator should send the message /invite @username to the bot. "
                    "The admin will receive a message about the successful operation, and the user should press the start button "
                    "in the bot again to gain access to the team functions."
                )
            
            await message.reply(
                f"🏢 Team Information:\n\n"
                f"Name: {team.name}\n"
                f"Number of team members: {member_count}\n"
                f"{admin_status}{admin_commands}\n\n"
                f"Use /leave_team to leave this team. You will need to enter a confirmation code to exit the team."
            )
            
        except Exception as e:
            from app.core.logging import logger
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
    
    async def cmd_leave_team(self, message: types.Message, state: FSMContext):
        """Handler for /leave_team command"""
        try:
            # Проверяем, состоит ли пользователь в команде
            team = await self.team_service.get_user_team(message.from_user.id)
            if not team:
                await message.reply("You are not a member of any team")
                return
            
            # Получаем текущее состояние пользователя
            current_state = await state.get_state()
            
            # Если пользователь еще не в состоянии подтверждения, генерируем код
            if current_state != LeaveTeamStates.waiting_for_confirmation.state:
                # Генерируем код подтверждения
                confirmation_code = generate_confirmation_code()
                
                # Сохраняем код в состоянии пользователя
                await state.set_state(LeaveTeamStates.waiting_for_confirmation)
                await state.update_data(confirmation_code=confirmation_code)
                
                await message.reply(
                    f"⚠️ Are you sure you want to leave the team '{team.name}'?\n\n"
                    f"This action cannot be undone. To confirm, please enter the following code:\n\n"
                    f"{confirmation_code}\n\n"
                    f"If you changed your mind, use /cancel to abort."
                )
                return
            
            # Если пользователь уже в состоянии подтверждения, проверяем код
            user_data = await state.get_data()
            saved_code = user_data.get('confirmation_code')
            user_input = message.text.strip()
            
            if user_input == saved_code:
                # Код верный, выполняем выход из команды
                success, result_message = await self.team_service.leave_team(
                    telegram_id=message.from_user.id
                )
                
                # Сбрасываем состояние
                await state.clear()
                
                if success:
                    # Если пользователь успешно вышел из команды, возвращаем начальную клавиатуру
                    from app.bot.handlers.base import get_initial_keyboard
                    await message.reply(
                        result_message + "\n\nYou have left your team. Some functions are now unavailable.",
                        reply_markup=get_initial_keyboard()
                    )
                else:
                    await message.reply(result_message)
                    
                logger.info(f"User {message.from_user.id} left team: {success}")
            else:
                # Код неверный
                await message.reply(
                    "❌ Incorrect confirmation code. Please try again or use /cancel to abort."
                )
                
        except Exception as e:
            logger.error(f"Error leaving team: {e}", exc_info=True)
            await message.reply("An error occurred while leaving the team")
            # Сбрасываем состояние в случае ошибки
            await state.clear()

    async def cmd_cancel(self, message: types.Message, state: FSMContext):
        """Handler for /cancel command"""
        current_state = await state.get_state()
        if current_state is None:
            await message.reply("Nothing to cancel.")
            return
        
        await state.clear()
        await message.reply("Action canceled.")

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
     # Добавляем обработчик для команды cancel
    router.message.register(
        handlers.cmd_cancel,
        Command("cancel")
    )
    # Добавляем обработчик для проверки кода подтверждения
    router.message.register(
        handlers.cmd_leave_team,
        LeaveTeamStates.waiting_for_confirmation
    )
    return router 
