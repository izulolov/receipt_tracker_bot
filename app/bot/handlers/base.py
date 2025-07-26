# app/bot/handlers/base.py
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from app.core.logging import logger
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.services.team_service import TeamService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, team_service: TeamService = None):
    try:
        name = message.from_user.first_name
        
        # Проверяем, состоит ли пользователь в команде
        has_team = False
        if team_service:
            team = await team_service.get_user_team(message.from_user.id)
            has_team = team is not None
        
        welcome_text = f"👋 Hello, {name}! I'm a bot for managing receipts and expenses.\n\n"
        
        if has_team:
            # Если пользователь уже в команде
            welcome_text += (
                "Here's what I can do:\n"
                "• Upload and analyze receipts\n"
                "• Track expenses by categories\n"
                "• Work with teams for collaborative expense tracking\n\n"
                "Use the /help command for detailed information about available commands."
            )
            keyboard = get_full_keyboard()
        else:
            # Если пользователь еще не в команде
            welcome_text += (
                "To start using all the bot's functions, first create a team.\n\n"
                "Use the command /create_team Team_name to create a new team.\n\n"
                "After creating a team, all bot functions will become available to you."
            )
            keyboard = get_initial_keyboard()
        
        await message.answer(
            welcome_text,
            reply_markup=keyboard
        )
        logger.info(f"User {message.from_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "Sorry, something went wrong. Please try again later.")


# Добавляем обработчик команды help
@router.message(Command("help"))
async def cmd_help(message: types.Message, team_service: TeamService = None):
    try:
        # Проверяем, состоит ли пользователь в команде
        has_team = False
        if team_service:
            team = await team_service.get_user_team(message.from_user.id)
            has_team = team is not None
        
        base_commands = (
            "• /start - Start the bot and see the welcome message\n\n"
            "• /create_team - Create a new team: `/create_team Team_name`\n\n"
            "• /help - Show this help message\n\n"
        )
        
        team_commands = (
            "• /upload_receipt - Upload a new receipt for processing and analysis\n\n"
            "• /list_receipts - View your receipts with various options:\n"
            "  - Without parameters: shows all receipts for the current month\n"
            "  - With one date: `/list_receipts 15.07.2025` shows receipts for this date\n"
            "  - With date range: `/list_receipts 15.07.2025 20.07.2025` shows receipts between these dates\n\n"
            "• /invite - Invite a user to your team: `/invite @username`\n\n"
            "• /team_info - Show information about your current team\n\n"
            "• /leave_team - Leave your current team\n\n"
        )
        
        help_text = "📋 Bot usage help\n\n✅ Available commands:\n\n"
        
        if has_team:
            help_text += base_commands + team_commands
        else:
            help_text += (
                base_commands + 
                "\nℹ️ After creating a team, additional commands for working with receipts and team management will become available."
            )
        
        help_text += (
            "Tips:\n"
            "- Use keyboard buttons for quick access to commands\n"
            "- When uploading receipts, make sure the image is clear and readable\n"
            "- You can always enter commands manually if needed"
        )
        
        # Отправляем без использования Markdown-форматирования
        await message.answer(help_text)
        logger.info(f"User {message.from_user.id} requested help")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.answer(
            "Sorry, something went wrong. Please try again later.")
        
# Клавиатура для пользователя без команды
def get_initial_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/create_team"),
                KeyboardButton(text="/help"),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Select a command or enter a message",
        is_persistent=True
    )
    return keyboard

# Полная клавиатура для пользователя с командой
def get_full_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/upload_receipt"),
                KeyboardButton(text="/list_receipts"),
            ],
            [
                KeyboardButton(text="/team_info"),
                KeyboardButton(text="/invite"),
            ],
            [
                KeyboardButton(text="/help"),
                KeyboardButton(text="/leave_team"),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Select a command or enter a message",
        is_persistent=True
    )
    return keyboard