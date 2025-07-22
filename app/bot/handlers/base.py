# app/bot/handlers/base.py
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from app.core.logging import logger
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    try:
        name = message.from_user.first_name
        await message.answer(
            f"👋 Welcome {name}! I'm your receipt management bot.\n\n"
            "Here's what I can do:\n"
            "/upload_receipt - Upload a new receipt\n"
            "/list_receipts - View your receipts\n"
            "/help - Show available commands",
            reply_markup=get_main_keyboard()  # Добавляем клавиатуру к сообщению
        )
        logger.info(f"User {message.from_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "Sorry, something went wrong. Please try again later.")


# Добавляем обработчик команды help
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    try:
        help_text = (
            "📋 Receipt Management Bot Help\n\n"
            "✅ Available Commands:\n\n"
            "• **/start** - Start the bot and see the welcome message\n\n"
            "• **/upload_receipt - Upload a new receipt for processing and analysis\n\n"
            "• /list_receipts** - View your receipts with different options:\n"
            "  - Without parameters: shows all receipts for the current month\n"
            "  - With one date: `/list_receipts 15.07.2025` shows receipts for that specific date\n"
            "  - With date range: `/list_receipts 15.07.2025 20.07.2025` shows receipts between these dates\n\n"
            "• **/help** - Show this help message with all available commands\n\n"
            "Tips:\n"
            "- Use the keyboard buttons for quick access to commands\n"
            "- When uploading receipts, make sure the image is clear and readable\n"
            "- You can always type a command manually if needed"
        )
        
        await message.answer(help_text, parse_mode="Markdown")
        logger.info(f"User {message.from_user.id} requested help")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.answer(
            "Sorry, something went wrong. Please try again later.")
        
# Создаем клавиатуру с командами
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/start"),
                KeyboardButton(text="/upload_receipt"),
            ],
            [
                KeyboardButton(text="/list_receipts"),
                KeyboardButton(text="/help"),
            ]
        ],
        resize_keyboard=True,  # Сделать кнопки меньше
        input_field_placeholder="Выберите команду или введите сообщение",
        is_persistent=True  # Сделать клавиатуру постоянной
    )
    return keyboard
