# app/bot/handlers/receipt.py
from datetime import datetime, timedelta
from typing import Union

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, Document, PhotoSize, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.services.receipt_service import ReceiptService
from app.services.team_service import TeamService
from app.core.config import Settings
from app.bot.handlers.base import get_full_keyboard

from app.core.logging import logger


# Определение состояний для FSM (Finite State Machine)
class ReceiptListStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()


def setup_receipt_handlers(
        receipt_service: ReceiptService,
        team_service: TeamService,
        settings: Settings
) -> Router:
    router = Router()
    handlers = ReceiptHandlers(receipt_service, team_service, settings)

    # Handle initial upload command
    router.message.register(
        handlers.cmd_upload_receipt,
        Command("upload_receipt")
    )

    # Handle file upload (after command)
    router.message.register(
        handlers.cmd_upload_receipt,
        F.document | F.photo
    )

    # Обработчик команды list_receipts
    router.message.register(
        handlers.cmd_list_receipts,
        Command("list_receipts")
    )
    
    # Обработчики для инлайн-кнопок
    router.callback_query.register(
        handlers.process_list_receipts_callback,
        F.data.startswith("receipts_")
    )
    
    # Обработчики для ввода дат
    router.message.register(
        handlers.process_date_input,
        ReceiptListStates.waiting_for_date
    )
    
    router.message.register(
        handlers.process_start_date_input,
        ReceiptListStates.waiting_for_start_date
    )
    
    router.message.register(
        handlers.process_end_date_input,
        ReceiptListStates.waiting_for_end_date
    )

    return router


class ReceiptHandlers:
    def __init__(
            self,
            receipt_service: ReceiptService,
            team_service: TeamService,
            settings: Settings
    ):
        self.receipt_service = receipt_service
        self.team_service = team_service
        self.settings = settings
        self.allowed_mime_types = {'image/jpeg', 'image/png',
                                   'application/pdf'}

    async def _validate_file(
            self, message: Message, file: Union[Document, PhotoSize]
    ) -> bool:
        """Validate file type and size."""
        if isinstance(file, Document):
            if file.mime_type not in self.allowed_mime_types:
                await message.reply(
                    "Invalid file type. Please send a PDF or image file.")
                return False
            if file.file_size > 20_000_000:  # 20MB limit
                await message.reply("File is too large. Maximum size is 20MB.")
                return False
        return True

    async def cmd_upload_receipt(self, message: Message):
        """Handle receipt upload command."""
        try:
            if not (message.document or message.photo):
                await message.reply(
                    "Please attach a receipt file (PDF or image) "
                    "with the /upload_receipt command")
                return

            file = message.document or message.photo[-1]
            if not await self._validate_file(message, file):
                return

            # Download file
            file_obj = await message.bot.get_file(file.file_id)
            file_content = await message.bot.download_file(file_obj.file_path)

            # Process receipt
            receipt, status_message = await self.receipt_service.process_receipt(
                telegram_id=message.from_user.id,
                file_data=file_content,
                filename=file_obj.file_path.split('/')[-1]
            )

            if receipt:
                # Форматирование полей для вывода
                date_str = receipt.date.strftime('%d-%m-%Y %H:%M:%S') if receipt.date else "N/A"
                amount_str = f"{receipt.amount}" if receipt.amount is not None else "N/A"
                status_str = receipt.status or "N/A"
                operation_number_str = receipt.operation_number if hasattr(receipt, 'operation_number') else "N/A"
                sender_str = receipt.sender if hasattr(receipt, 'sender') else "N/A"
                receiver_str = receipt.receiver if hasattr(receipt, 'receiver') else "N/A"
                organization_str = receipt.organization if hasattr(receipt, 'organization') else "N/A"
                fee_str = receipt.fee if hasattr(receipt, 'fee') else "0"
                notes_str = receipt.notes if hasattr(receipt, 'notes') else "N/A"
                # Для upload_by просто используем ID пользователя
                upload_by_str = str(message.from_user.username)
                
                # Формируем сообщение со всеми полями
                await message.reply(
                    f"Receipt processed successfully!\n\n"
                    f"📅 Date: {date_str}\n"
                    f"💰 Amount: {amount_str}\n"
                    f"📊 Status: {status_str}\n"
                    f"🔢 Operation #: {operation_number_str}\n"
                    f"📤 Sender: {sender_str}\n"
                    f"📥 Receiver: {receiver_str}\n"
                    f"🏢 Organization: {organization_str}\n"
                    f"💸 Fee: {fee_str}\n"
                    f"📝 Notes: {notes_str}\n"
                    f"👤 Uploaded by: {upload_by_str}"
                )
            else:
                await message.reply(
                    f"Failed to process receipt: {status_message}")

        except Exception as e:
            logger.error(f"Error processing receipt: {e}", exc_info=True)
            await message.reply(
                "An error occurred while processing the receipt. "
                "Please try again later.")

    async def cmd_list_receipts(self, message: Message, state: FSMContext = None):
        """Handle listing receipts command - show menu with options."""
        try:
            # Создаем инлайн-клавиатуру с опциями
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Последние 5 чеков", callback_data="receipts_last5")],
                [InlineKeyboardButton(text="📅 За последний месяц", callback_data="receipts_month")],
                [InlineKeyboardButton(text="📆 За конкретную дату", callback_data="receipts_date")],
                [InlineKeyboardButton(text="📊 За период", callback_data="receipts_period")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="receipts_back")]
            ])
            
            await message.reply(
                "Выберите период для просмотра чеков:",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing receipt list menu: {e}", exc_info=True)
            await message.reply(
                "Произошла ошибка при отображении меню. "
                "Пожалуйста, попробуйте позже.")
    
    async def process_list_receipts_callback(self, callback_query: CallbackQuery, state: FSMContext = None):
        """Process callback from list_receipts menu."""
        try:
            action = callback_query.data.split('_')[1]
            
            if action == "back":
                # Вместо редактирования текущего сообщения, отправляем новое сообщение с меню
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Последние 5 чеков", callback_data="receipts_last5")],
                    [InlineKeyboardButton(text="📅 За последний месяц", callback_data="receipts_month")],
                    [InlineKeyboardButton(text="📆 За конкретную дату", callback_data="receipts_date")],
                    [InlineKeyboardButton(text="📊 За период", callback_data="receipts_period")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="receipts_back")]
                ])
                
                await callback_query.message.reply(
                    "Выберите период для просмотра чеков:",
                    reply_markup=keyboard
                )
                await callback_query.answer("Возврат в меню чеков")
                return
                    
            elif action == "last5":
                # Показать последние 5 чеков
                today = datetime.now()
                # Устанавливаем дату начала на 1 год назад
                start_date = today - timedelta(days=365)
                end_date = today
                limit = 5
                
                await self._show_receipts(
                    callback_query.message, 
                    callback_query.from_user.id,
                    start_date, 
                    end_date,
                    limit=limit,
                    period_description="последние 5 чеков"
                )
                await callback_query.answer()
                
            elif action == "month":
                # Показать чеки за последний месяц
                today = datetime.now()
                start_date = today - timedelta(days=30)
                end_date = today
                
                await self._show_receipts(
                    callback_query.message, 
                    callback_query.from_user.id,
                    start_date, 
                    end_date,
                    period_description="последние 30 дней"
                )
                await callback_query.answer()
                
            elif action == "date":
                # Запросить конкретную дату - отправляем новое сообщение вместо редактирования
                await callback_query.message.reply(
                    "Введите дату в формате ДД-ММ-ГГГГ (например, 15-07-2025):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                    ])
                )
                if state:
                    await state.set_state(ReceiptListStates.waiting_for_date)
                await callback_query.answer()
                
            elif action == "period":
                # Запросить начальную дату периода - отправляем новое сообщение вместо редактирования
                await callback_query.message.reply(
                    "Введите начальную дату периода в формате ДД-ММ-ГГГГ (например, 01-07-2025):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                    ])
                )
                if state:
                    await state.set_state(ReceiptListStates.waiting_for_start_date)
                await callback_query.answer()
                
        except Exception as e:
            logger.error(f"Error processing receipt list callback: {e}", exc_info=True)
            await callback_query.message.reply(
                "Произошла ошибка при обработке запроса. "
                "Пожалуйста, попробуйте позже.")
            await callback_query.answer()
    
    async def process_date_input(self, message: Message, state: FSMContext):
        """Process input for specific date."""
        try:
            # Очищаем состояние
            if state:
                await state.clear()
            
            try:
                # Пытаемся распарсить дату
                date = datetime.strptime(message.text, '%d-%m-%Y')
                start_date = date
                end_date = date.replace(hour=23, minute=59, second=59)
                
                await self._show_receipts(
                    message, 
                    message.from_user.id,
                    start_date, 
                    end_date,
                    period_description=f"дату {message.text}"
                )
                
            except ValueError:
                await message.reply(
                    "Неверный формат даты. Используйте формат ДД-ММ-ГГГГ (например, 15-07-2025).",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                    ])
                )
                
        except Exception as e:
            logger.error(f"Error processing date input: {e}", exc_info=True)
            await message.reply(
                "Произошла ошибка при обработке даты. "
                "Пожалуйста, попробуйте позже.",
                reply_markup=get_full_keyboard()
            )
    
    async def process_start_date_input(self, message: Message, state: FSMContext):
        """Process input for start date of period."""
        try:
            try:
                # Пытаемся распарсить дату
                start_date = datetime.strptime(message.text, '%d-%m-%Y')
                
                # Сохраняем начальную дату в состоянии
                if state:
                    await state.update_data(start_date=start_date)
                    await state.set_state(ReceiptListStates.waiting_for_end_date)
                
                await message.reply(
                    "Теперь введите конечную дату периода в формате ДД-ММ-ГГГГ (например, 31-07-2025):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                    ])
                )
                
            except ValueError:
                await message.reply(
                    "Неверный формат даты. Используйте формат ДД-ММ-ГГГГ (например, 01-07-2025).",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                    ])
                )
                
        except Exception as e:
            logger.error(f"Error processing start date input: {e}", exc_info=True)
            await message.reply(
                "Произошла ошибка при обработке начальной даты. "
                "Пожалуйста, попробуйте позже.",
                reply_markup=get_full_keyboard()
            )
    
    async def process_end_date_input(self, message: Message, state: FSMContext):
        """Process input for end date of period."""
        try:
            # Очищаем состояние в конце
            if not state:
                await message.reply(
                    "Произошла ошибка с состоянием. Пожалуйста, начните сначала.",
                    reply_markup=get_full_keyboard()
                )
                return
                
            try:
                # Получаем начальную дату из состояния
                data = await state.get_data()
                start_date = data.get('start_date')
                
                if not start_date:
                    await message.reply(
                        "Произошла ошибка с начальной датой. Пожалуйста, начните сначала.",
                        reply_markup=get_full_keyboard()
                    )
                    await state.clear()
                    return
                
                # Пытаемся распарсить конечную дату
                end_date = datetime.strptime(message.text, '%d-%m-%Y').replace(hour=23, minute=59, second=59)
                
                # Проверяем, что конечная дата не раньше начальной
                if end_date < start_date:
                    await message.reply(
                        "Конечная дата не может быть раньше начальной. Пожалуйста, введите корректную дату.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                        ])
                    )
                    return
                
                # Очищаем состояние
                await state.clear()
                
                # Показываем чеки за выбранный период
                await self._show_receipts(
                    message, 
                    message.from_user.id,
                    start_date, 
                    end_date,
                    period_description=f"период с {start_date.strftime('%d-%m-%Y')} по {end_date.strftime('%d-%m-%Y')}"
                )
                
            except ValueError:
                await message.reply(
                    "Неверный формат даты. Используйте формат ДД-ММ-ГГГГ (например, 31-07-2025).",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                    ])
                )
                
        except Exception as e:
            logger.error(f"Error processing end date input: {e}", exc_info=True)
            await message.reply(
                "Произошла ошибка при обработке конечной даты. "
                "Пожалуйста, попробуйте позже.",
                reply_markup=get_full_keyboard()
            )
            if state:
                await state.clear()
    
    async def _show_receipts(self, message: Message, telegram_id: int, start_date: datetime, end_date: datetime, 
                            limit: int = None, period_description: str = ""):
        """Show receipts for the given period."""
        try:
            # Получаем чеки за указанный период
            receipts, total_count = await self.receipt_service.get_user_receipts(
                telegram_id=telegram_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )

            if not receipts:
                await message.reply(
                    f"Чеки за {period_description} не найдены",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                    ])
                )
                return

            # Форматируем детальную информацию о каждом чеке
            receipt_details = []
            total_amount = 0

            # Используем порядковый номер вместо ID из базы данных
            for index, r in enumerate(receipts, 1):
                total_amount += float(r.amount) if r.amount else 0
                
                # Форматирование полей для вывода
                date_str = r.date.strftime('%d-%m-%Y %H:%M') if r.date else "N/A"
                creation_at_str = r.creation_at.strftime('%d-%m-%Y %H:%M') if hasattr(r, 'creation_at') and r.creation_at else "N/A"
                amount_str = f"{r.amount}" if r.amount is not None else "N/A"
                status_str = r.status or "N/A"
                operation_number_str = r.operation_number if hasattr(r, 'operation_number') and r.operation_number else "N/A"
                organization_str = r.organization if hasattr(r, 'organization') and r.organization else "N/A"
                
                receipt_details.append(
                    f"📝 Чек #{index}\n"  # Используем порядковый номер вместо r.id
                    f"📅 Дата чека: {date_str}\n"
                    f"⏱️ Дата загрузки: {creation_at_str}\n"
                    f"💰 Сумма: {amount_str}\n"
                    f"🏢 Организация: {organization_str}\n"
                    f"🔢 Номер операции: {operation_number_str}\n"
                    f"📊 Статус: {status_str}\n"
                )

            # Формируем общую информацию
            header = (
                f"📋 Чеки за {period_description}\n"
                f"📊 Всего чеков: {len(receipts)}\n"
                f"💰 Общая сумма: {total_amount:.2f}\n\n"
            )

            # Добавляем кнопку "Назад" в конце сообщения
            back_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
            ])

            # Разбиваем на части, если сообщение слишком длинное
            max_message_length = 4000  # Максимальная длина сообщения в Telegram
            current_message = header
            
            for i, detail in enumerate(receipt_details):
                if len(current_message + detail + "\n") > max_message_length:
                    # Для всех сообщений кроме последнего не добавляем кнопку
                    await message.reply(current_message)
                    current_message = detail + "\n"
                else:
                    current_message += detail + "\n"
                    
            if current_message:
                # Только для последнего сообщения добавляем кнопку "Назад"
                await message.reply(current_message, reply_markup=back_button)

        except Exception as e:
            logger.error(f"Error showing receipts: {e}", exc_info=True)
            await message.reply(
                "Произошла ошибка при получении чеков. "
                "Пожалуйста, попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к меню чеков", callback_data="receipts_back")]
                ])
            )
