from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.services.file_storage import FileStorageService
from app.services.ocr import OCRProcessingError, OCRService
from app.repositories.receipt import ReceiptRepository
from app.models.receipt import Receipt


class ReceiptProcessor:
    def __init__(
            self,
            session: AsyncSession,
            file_storage: FileStorageService,
            ocr_service: OCRService
    ):
        self.repository = ReceiptRepository(session)
        self.file_storage = file_storage
        self.ocr_service = ocr_service

    async def process_receipt(
            self,
            team_id: int,
            user_id: int,
            file_data: bytes,
            filename: str
    ) -> Receipt:
        try:
            # Save file
            file_path = await self.file_storage.save_file(
                file_data,
                filename
            )

            # Process with OCR
            receipt_data = await self.ocr_service.process_document(
                file_path
            )

            if not receipt_data.get('amount') or not receipt_data.get('date'):
                raise ValueError(
                    "Could not extract required information from receipt"
                )

            # Prepare receipt data
            receipt_data = self._prepare_receipt_data(
                receipt_data,
                team_id,
                user_id,
                str(file_path)
            )

            # Save to database
            return await self.repository.create(**receipt_data)

        except OCRProcessingError as e:
            # Log error and raise appropriate exception
            logger.error(f"OCR processing failed: {str(e)}")
            raise ValueError("Failed to process receipt")

    def _prepare_receipt_data(
            self,
            ocr_data: Dict[str, Any],
            team_id: int,
            user_id: int,
            file_path: str
    ) -> Dict[str, Any]:
        # Обрабатываем дату
        date_value = ocr_data.get('date')
        if isinstance(date_value, datetime):
            date = date_value
        elif isinstance(date_value, str):
            try:
                date = datetime.strptime(date_value, '%Y-%m-%d')
            except ValueError:
                try:
                    date = datetime.strptime(date_value, '%d.%m.%Y')
                except ValueError:
                    date = datetime.now()
        else:
            date = datetime.now()
        
        # Обрабатываем сумму
        amount = ocr_data.get('amount')
        if amount is not None:
            amount = Decimal(str(amount))
        
        # Обрабатываем комиссию
        fee = ocr_data.get('fee')
        if fee is not None:
            fee = Decimal(str(fee))
        
        return {
            'team_id': team_id,
            'uploaded_by': user_id,
            'date': date,
            'amount': amount,
            'operation_number': ocr_data.get('operation_number'),
            'sender': ocr_data.get('sender'),
            'receiver': ocr_data.get('receiver'),
            'status': 'pending',
            'file_path': file_path,
            'organization': ocr_data.get('organization'),
            'fee': fee,
            'notes': ocr_data.get('notes')
        }