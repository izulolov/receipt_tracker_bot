# app/bot/handlers/receipt.py
from datetime import datetime, timedelta
from typing import Union

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, Document, PhotoSize

from app.services.receipt_service import ReceiptService
from app.services.team_service import TeamService
from app.core.config import Settings

from app.core.logging import logger


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

    router.message.register(
        handlers.cmd_list_receipts,
        Command("list_receipts")
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

    async def cmd_list_receipts(self, message: Message):
        """Handle listing receipts command."""
        try:
            # Получаем текст сообщения и удаляем команду из него
            full_command = message.text.strip() if message.text else ""
            args = []
            
            # Извлекаем аргументы из текста сообщения
            if full_command.startswith('/list_receipts'):
                # Удаляем команду из текста и разбиваем оставшуюся часть на аргументы
                command_parts = full_command.split(maxsplit=1)
                if len(command_parts) > 1:
                    args = command_parts[1].split()
            
            # Если аргументы не указаны или указан только один аргумент (одна дата)
            if len(args) == 0:
                # Если дата не указана, используем текущий месяц
                today = datetime.now()
                start_date = datetime(today.year, today.month, 1)
                
                # Определяем последний день текущего месяца
                if today.month == 12:
                    end_date = datetime(today.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
                    
                end_date = end_date.replace(hour=23, minute=59, second=59)
            elif len(args) == 1:
                # Если указана только одна дата, используем ее как начало и конец периода
                try:
                    date = datetime.strptime(args[0], '%Y-%m-%d')
                    start_date = date
                    end_date = date.replace(hour=23, minute=59, second=59)
                except ValueError:
                    await message.reply(
                        "Неверный формат даты. Используйте формат YYYY-MM-DD")
                    return
            else:
                # Если указаны две даты, используем их как начало и конец периода
                try:
                    start_date = datetime.strptime(args[0], '%Y-%m-%d')
                    end_date = datetime.strptime(args[1], '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                except ValueError:
                    await message.reply(
                        "Неверный формат даты. Используйте формат YYYY-MM-DD")
                    return

            receipts = await self.receipt_service.get_user_receipts(
                telegram_id=message.from_user.id,
                start_date=start_date,
                end_date=end_date
            )

            if not receipts:
                date_range = f"{start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}"
                if start_date.date() == end_date.date():
                    date_range = f"{start_date.strftime('%Y-%m-%d')}"
                    
                await message.reply(
                    f"Чеки за период {date_range} не найдены")
                return

            # Форматируем детальную информацию о каждом чеке
            receipt_details = []
            total_amount = 0

            for r in receipts:
                total_amount += float(r.amount) if r.amount else 0
                
                # Форматирование полей для вывода
                date_str = r.date.strftime('%d-%m-%Y %H:%M') if r.date else "N/A"
                amount_str = f"{r.amount}" if r.amount is not None else "N/A"
                status_str = r.status or "N/A"
                operation_number_str = r.operation_number if hasattr(r, 'operation_number') and r.operation_number else "N/A"
                organization_str = r.organization if hasattr(r, 'organization') and r.organization else "N/A"
                
                receipt_details.append(
                    f"📝 Чек #{r.id}\n"
                    f"📅 Дата: {date_str}\n"
                    f"💰 Сумма: {amount_str}\n"
                    f"🏢 Организация: {organization_str}\n"
                    f"🔢 Номер операции: {operation_number_str}\n"
                    f"📊 Статус: {status_str}\n"
                )

            # Формируем общую информацию
            date_range = f"{start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}"
            if start_date.date() == end_date.date():
                date_range = f"{start_date.strftime('%Y-%m-%d')}"
                
            header = (
                f"📋 Чеки за период: {date_range}\n"
                f"📊 Всего чеков: {len(receipts)}\n"
                f"💰 Общая сумма: {total_amount:.2f}\n\n"
            )

            # Разбиваем на части, если сообщение слишком длинное
            max_message_length = 4000  # Максимальная длина сообщения в Telegram
            current_message = header
            
            for detail in receipt_details:
                if len(current_message + detail + "\n") > max_message_length:
                    await message.reply(current_message)
                    current_message = detail + "\n"
                else:
                    current_message += detail + "\n"
                    
            if current_message:
                await message.reply(current_message)

        except Exception as e:
            logger.error(f"Error listing receipts: {e}", exc_info=True)
            await message.reply(
                "Произошла ошибка при получении чеков. "
                "Пожалуйста, попробуйте позже.")