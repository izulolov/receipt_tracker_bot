from datetime import datetime
from typing import Optional, List, Tuple, BinaryIO
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
            filename: str
    ) -> Tuple[Optional[Receipt], str]:
        """Process and store a new receipt."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return None, "User not found"

        team_id = user.id # Временное решение, так как в данном этапе не очень понимаю что за team*

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_data.read())
                temp_path = Path(temp_file.name)

            # Process receipt using ReceiptProcessor
            receipt = await self.receipt_processor.process_receipt(
                team_id=team_id, # *
                user_id=user.id,
                file_data=temp_path.read_bytes(),
                filename=filename
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

    async def get_user_receipts(
            self,
            telegram_id: int,
            start_date: datetime,
            end_date: datetime
    ) -> List[Receipt]:
        """Get user's receipts for date range."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return []

        # Временное решение: используем user.id как team_id. Это как в методе process_receipt
        team_id = user.id

        return await self.receipt_repository.get_team_receipts_in_period(
            team_id,
            start_date,
            end_date
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
                status=status
            )
            return True, "Receipt status updated successfully"
        except Exception as e:
            return False, f"Failed to update receipt status: {str(e)}"
