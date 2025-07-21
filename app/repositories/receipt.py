from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_
from app.models.receipt import Receipt
from .base import BaseRepository


class ReceiptRepository(BaseRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.model = Receipt

    async def get_team_receipts_in_period(
            self,
            team_id: int,
            start_date: datetime,
            end_date: datetime
    ) -> List[Receipt]:
        async with self.session_factory() as session:
            stmt = (
                select(Receipt)
                .where(
                    and_(
                        Receipt.team_id == team_id,
                        Receipt.date >= start_date,
                        Receipt.date <= end_date
                    )
                )
                .order_by(Receipt.date)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create_receipt(
            self,
            team_id: int,
            user_id: int,
            amount: float,
            date: datetime,
            file_path: str,
            status: str = "pending"
    ) -> Receipt:
        return await self.create(
            team_id=team_id,
            user_id=user_id,
            amount=amount,
            date=date,
            file_path=file_path,
            status=status
        )
