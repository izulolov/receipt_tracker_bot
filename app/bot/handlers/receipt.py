# app/bot/handlers/receipt.py
from datetime import datetime
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
                await message.reply(
                    f"Receipt processed successfully!\n"
                    f"Amount: {receipt.amount}\n"
                    f"Date: {receipt.date.strftime('%Y-%m-%d')}\n"
                    f"Status: {receipt.status}"
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
            args = message.get_args().split()
            if len(args) != 2:
                await message.reply(
                    "Please provide start and end dates: "
                    "/list_receipts YYYY-MM-DD YYYY-MM-DD")
                return

            try:
                start_date = datetime.strptime(args[0], '%Y-%m-%d')
                end_date = datetime.strptime(args[1], '%Y-%m-%d')
            except ValueError:
                await message.reply(
                    "Invalid date format. Please use YYYY-MM-DD")
                return

            receipts = await self.receipt_service.get_user_receipts(
                telegram_id=message.from_user.id,
                start_date=start_date,
                end_date=end_date
            )

            if not receipts:
                await message.reply(
                    f"No receipts found between {args[0]} and {args[1]}")
                return

            # Format receipts summary
            total_amount = sum(float(r.amount) for r in receipts)
            receipt_list = [
                f"Receipt {r.id}: {r.date.strftime('%Y-%m-%d')} - "
                f"Amount: {r.amount} - Status: {r.status}"
                for r in receipts
            ]

            response = (
                    f"Receipts for period: {args[0]} to {args[1]}\n"
                    f"Total receipts: {len(receipts)}\n"
                    f"Total amount: {total_amount:.2f}\n\n"
                    + "\n".join(receipt_list)
            )

            await message.reply(response)

        except Exception as e:
            logger.error(f"Error listing receipts: {e}", exc_info=True)
            await message.reply(
                "An error occurred while retrieving receipts. "
                "Please try again later.")