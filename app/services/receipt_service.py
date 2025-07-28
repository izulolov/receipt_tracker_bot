from datetime import datetime
from typing import Optional, List, Tuple, BinaryIO, Dict, Any
from pathlib import Path
import tempfile

from app.models.receipt import Receipt
from app.repositories.receipt import ReceiptRepository
from app.repositories.team import TeamRepository
from app.repositories.user import UserRepository
from app.services.base import BaseService
from app.services.file_storage import FileStorageService
from app.services.ocr import OCRService, OCRProcessingError
from app.services.ocr.receipt_processor import ReceiptProcessor
from sqlalchemy import select, func

class ReceiptService(BaseService):
    def __init__(self, session, upload_dir):
        super().__init__(session)
        self.receipt_repository = ReceiptRepository(session)
        self.team_repository = TeamRepository(session)
        self.user_repository = UserRepository(session)

        # Initialize required services
        self.file_storage = FileStorageService(upload_dir=upload_dir)
        self.ocr_service = OCRService()
        self.receipt_processor = ReceiptProcessor(
            session=session,
            file_storage=self.file_storage,
            ocr_service=self.ocr_service
        )

    async def process_receipt(
            self,
            telegram_id: int,
            file_data: BinaryIO,
            filename: str,
            description: str = ""
    ) -> Tuple[Optional[Receipt], str]:
        """Process and store a new receipt."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return None, "User not found"

        # Получаем команду пользователя
        team = await self.team_repository.get_user_team(user.id)
        if not team:
            return None, "User is not a member of any team"

        team_id = team.id

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_data.read())
                temp_path = Path(temp_file.name)

            # Process receipt using ReceiptProcessor
            receipt = await self.receipt_processor.process_receipt(
                team_id=team_id,
                user_id=user.id,
                file_data=temp_path.read_bytes(),
                filename=filename,
                description=description
            )

            # Clean up temporary file
            temp_path.unlink()

            return receipt, "Receipt processed successfully"

        except OCRProcessingError as e:
            return None, f"OCR processing failed: {str(e)}"
        except ValueError as e:
            return None, str(e)
        except Exception as e:
            return None, f"Failed to process receipt: {str(e)}"

    async def get_user_receipts(self, telegram_id: int, start_date: datetime = None, 
                            end_date: datetime = None, limit: int = None):
        """Get user receipts for the given period."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return [], 0
            
        team = await self.team_repository.get_user_team(user.id)
        if not team:
            return [], 0
        
        # Получаем чеки пользователя за указанный период
        async with self.session() as session:
            query = select(Receipt).where(
                Receipt.team_id == team.id,
                Receipt.uploaded_by == user.id
            )
            
            # Добавляем фильтрацию по датам, если они указаны
            # Используем creation_at вместо date для фильтрации
            if start_date:
                query = query.where(Receipt.creation_at >= start_date)
            if end_date:
                query = query.where(Receipt.creation_at <= end_date)
            
            # Сортируем по дате создания (сначала новые)
            query = query.order_by(Receipt.creation_at.desc())
            
            # Применяем ограничение, если оно указано
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            receipts = list(result.scalars().all())
            
            # Получаем общее количество чеков (без лимита)
            count_query = select(func.count()).select_from(Receipt).where(
                Receipt.team_id == team.id,
                Receipt.uploaded_by == user.id
            )
            
            if start_date:
                count_query = count_query.where(Receipt.creation_at >= start_date)
            if end_date:
                count_query = count_query.where(Receipt.creation_at <= end_date)
                
            count_result = await session.execute(count_query)
            total_count = count_result.scalar() or 0
            
            return receipts, total_count

    async def get_user_receipts_in_period(
            self,
            telegram_id: int,
            start_date: datetime,
            end_date: datetime
    ) -> List[Receipt]:
        """Get user's receipts for date range."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return []

        # Получаем команду пользователя
        team = await self.team_repository.get_user_team(user.id)
        if not team:
            return []

        # Проверяем, является ли пользователь админом
        is_admin = await self.team_repository.is_admin(team.id, user.id)

        return await self.receipt_repository.get_team_receipts_in_period(
            team_id=team.id,
            start_date=start_date,
            end_date=end_date,
            user_id=user.id,
            is_admin=is_admin
        )

    async def update_receipt_status(
            self,
            receipt_id: int,
            status: str,
            admin_telegram_id: int
    ) -> Tuple[bool, str]:
        """Update receipt status (admin only)."""
        admin = await self.user_repository.get_by_telegram_id(
            admin_telegram_id)
        if not admin:
            return False, "Admin not found"

        receipt = await self.receipt_repository.get_by_id(receipt_id)
        if not receipt:
            return False, "Receipt not found"

        if not await self.team_repository.is_admin(receipt.team_id, admin.id):
            return False, "User is not team admin"

        try:
            await self.receipt_repository.update(
                receipt_id,
                status=status,
                is_read=True  # При обновлении статуса чек автоматически отмечается как прочитанный
            )
            return True, "Receipt status updated successfully"
        except Exception as e:
            return False, f"Failed to update receipt status: {str(e)}"
    
    async def mark_receipt_as_read(
            self,
            receipt_id: int,
            admin_telegram_id: int
    ) -> Tuple[bool, str]:
        """Mark receipt as read by admin."""
        admin = await self.user_repository.get_by_telegram_id(admin_telegram_id)
        if not admin:
            return False, "Admin not found"

        receipt = await self.receipt_repository.get_by_id(receipt_id)
        if not receipt:
            return False, "Receipt not found"

        if not await self.team_repository.is_admin(receipt.team_id, admin.id):
            return False, "User is not team admin"

        try:
            success = await self.receipt_repository.mark_receipt_as_read(receipt_id)
            if success:
                return True, "Receipt marked as read"
            return False, "Failed to mark receipt as read"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def get_unread_receipts_count(self, admin_telegram_id: int) -> int:
        """Get count of unread receipts for admin."""
        admin = await self.user_repository.get_by_telegram_id(admin_telegram_id)
        if not admin:
            return 0
            
        return await self.receipt_repository.get_unread_receipts_count(admin.id)
    
    async def get_receipt_details(self, receipt_id: int) -> Dict[str, Any]:
        """Get detailed information about a receipt."""
        receipt = await self.receipt_repository.get_by_id(receipt_id)
        if not receipt:
            return {}
            
        uploader = await self.user_repository.get_by_id(receipt.uploaded_by)
        
        return {
            "id": receipt.id,
            "date": receipt.date,
            "amount": float(receipt.amount),
            "operation_number": receipt.operation_number,
            "sender": receipt.sender,
            "receiver": receipt.receiver,
            "status": receipt.status,
            "file_path": receipt.file_path,
            "creation_at": receipt.creation_at,
            "description": receipt.description,
            "organization": receipt.organization,
            "fee": float(receipt.fee) if receipt.fee else None,
            "is_read": receipt.is_read,
            "uploader": {
                "id": uploader.id,
                "name": uploader.name,
                "telegram_id": uploader.telegram_id
            } if uploader else None
        }
