from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
import re
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
            filename: str,
            description: str = ""
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
                str(file_path),
                description
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
            file_path: str,
            description: str = ""
    ) -> Dict[str, Any]:
        # Обрабатываем дату
        date_value = ocr_data.get('date')
        if isinstance(date_value, datetime):
            date = date_value
        elif isinstance(date_value, str):
            try:
                # Пробуем разные форматы даты
                for fmt in ['%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M', '%d.%m.%Y', '%Y-%m-%d']:
                    try:
                        date = datetime.strptime(date_value, fmt)
                        break
                    except ValueError:
                        continue
                else:  # Если ни один формат не подошел
                    date = datetime.now()
            except Exception:
                date = datetime.now()
        else:
            date = datetime.now()
        
        # Обрабатываем сумму
        amount = ocr_data.get('amount')
        if amount is not None:
            if isinstance(amount, str):
                # Удаляем все нецифровые символы, кроме точки и запятой
                amount = re.sub(r'[^\d.,]', '', amount)
                # Заменяем запятую на точку
                amount = amount.replace(',', '.')
                try:
                    amount = Decimal(amount)
                except:
                    amount = Decimal('0')
            else:
                try:
                    amount = Decimal(str(amount))
                except:
                    amount = Decimal('0')
        else:
            amount = Decimal('0')
        
        # Проверяем, что сумма не слишком маленькая (не является датой)
        if amount < 1:
            # Возможно, это дата, а не сумма. Ищем другое число в данных
            raw_text = ocr_data.get('raw_text', '')
            if raw_text:
                # Ищем числа, которые могут быть суммами
                amount_matches = re.findall(r'\b(\d+[\.,]\d{2})\b', raw_text)
                if amount_matches:
                    # Исключаем числа, похожие на даты (например, 16.07)
                    filtered_amounts = []
                    for match in amount_matches:
                        parts = match.replace(',', '.').split('.')
                        if len(parts) == 2:
                            # Если первая часть больше 31, это вероятно сумма, а не дата
                            if int(parts[0]) > 31:
                                filtered_amounts.append(float(match.replace(',', '.')))
                            # Если после точки больше 2 цифр, это не дата
                            elif len(parts[1]) > 2:
                                filtered_amounts.append(float(match.replace(',', '.')))
                            # Если после точки ровно 2 цифры и число большое, это вероятно сумма
                            elif len(parts[1]) == 2 and float(match.replace(',', '.')) > 100:
                                filtered_amounts.append(float(match.replace(',', '.')))
                    
                    if filtered_amounts:
                        # Берем максимальное значение как сумму
                        amount = Decimal(str(max(filtered_amounts)))
        
        # Обрабатываем комиссию
        fee = ocr_data.get('fee')
        if fee is not None:
            if isinstance(fee, str):
                # Удаляем все нецифровые символы, кроме точки и запятой
                fee = re.sub(r'[^\d.,]', '', fee)
                # Заменяем запятую на точку
                fee = fee.replace(',', '.')
                if fee:
                    try:
                        fee = Decimal(fee)
                    except:
                        fee = None
                else:
                    fee = Decimal('0')
            else:
                try:
                    fee = Decimal(str(fee))
                except:
                    fee = None
        
        # Проверяем наличие обязательных полей
        operation_number = ocr_data.get('operation_number')
        if operation_number is None or operation_number == '':
            # Пытаемся извлечь номер операции из raw_text
            raw_text = ocr_data.get('raw_text', '')
            if raw_text:
                # Ищем любые последовательности цифр и букв, которые могут быть номером операции
                op_matches = re.findall(r'\b([A-Z0-9/-]{6,})\b', raw_text)
                if op_matches:
                    operation_number = op_matches[0]
                else:
                    operation_number = 'UNKNOWN'
            else:
                operation_number = 'UNKNOWN'
        
        # Формируем данные для создания чека
        receipt_data = {
                'team_id': team_id,
                'uploaded_by': user_id,  # Изменено с user_id на uploaded_by
                'date': date,
                'amount': amount,
                'operation_number': operation_number,
                'sender': ocr_data.get('sender', ''),
                'receiver': ocr_data.get('receiver', ''),
                'status': 'pending',
                'file_path': file_path,
                'organization': ocr_data.get('organization', ''),
                'fee': fee,
                'notes': description,  # Используем description как notes
                'is_read': False  # Новый чек всегда непрочитанный
            }
                
        return receipt_data