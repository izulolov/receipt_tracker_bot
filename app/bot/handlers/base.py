# app/bot/handlers/base.py
from aiogram import Router, types
from aiogram.filters import CommandStart
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