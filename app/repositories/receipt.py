from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_, func
from app.models.receipt import Receipt
from app.models.team import Team, TeamMember
from .base import BaseRepository


class ReceiptRepository(BaseRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.model = Receipt

    async def get_user_receipts(
            self, 
            user_id: int, 
            limit: int = 10, 
            offset: int = 0
    ) -> List[Receipt]:
        """
        Получить чеки пользователя.
        Если пользователь админ - получает все чеки команды
        Если обычный пользователь - только свои чеки
        """
        async with self.session_factory() as session:
            # Проверяем, является ли пользователь админом в команде
            admin_query = select(TeamMember).where(
                TeamMember.user_id == user_id,
                TeamMember.is_admin == True
            )
            admin_result = await session.execute(admin_query)
            admin_member = admin_result.scalar_one_or_none()
            
            if admin_member:
                # Если админ, получаем все чеки команды
                team_query = select(Team).join(TeamMember).where(
                    TeamMember.user_id == user_id,
                    TeamMember.is_admin == True
                )
                team_result = await session.execute(team_query)
                team = team_result.scalar_one_or_none()
                
                if team:
                    query = select(Receipt).where(
                        Receipt.team_id == team.id
                    ).order_by(Receipt.date.desc()).limit(limit).offset(offset)
                else:
                    # Если у админа нет команды, возвращаем только его чеки
                    query = select(Receipt).where(
                        Receipt.uploaded_by == user_id
                    ).order_by(Receipt.date.desc()).limit(limit).offset(offset)
            else:
                # Если обычный пользователь, получаем только его чеки
                query = select(Receipt).where(
                    Receipt.uploaded_by == user_id
                ).order_by(Receipt.date.desc()).limit(limit).offset(offset)
            
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_team_receipts_in_period(
            self,
            team_id: int,
            start_date: datetime,
            end_date: datetime,
            user_id: Optional[int] = None,
            is_admin: bool = False
    ) -> List[Receipt]:
        """
        Получить чеки команды за период.
        Если пользователь админ - получает все чеки команды
        Если обычный пользователь - только свои чеки
        """
        async with self.session_factory() as session:
            base_query = (
                select(Receipt)
                .where(
                    Receipt.team_id == team_id,
                    Receipt.date >= start_date,
                    Receipt.date <= end_date
                )
            )
            
            # Если пользователь не админ, фильтруем только его чеки
            if not is_admin and user_id is not None:
                base_query = base_query.where(Receipt.uploaded_by == user_id)
                
            base_query = base_query.order_by(Receipt.date)
            
            result = await session.execute(base_query)
            return result.scalars().all()

    async def create_receipt(
            self,
            team_id: int,
            uploaded_by: int,
            amount: float,
            date: datetime,
            file_path: str,
            description: str = "",
            status: str = "pending",
            is_read: bool = False,
            operation_number: str = None,
            sender: str = None,
            receiver: str = None,
            organization: str = None,
            fee: float = None,
            notes: str = None
    ) -> Receipt:
        """Создать новый чек с указанием статуса прочтения"""
        return await self.create(
            team_id=team_id,
            uploaded_by=uploaded_by,  # Изменено с user_id на uploaded_by
            amount=amount,
            date=date,
            file_path=file_path,
            status=status,
            is_read=is_read,
            operation_number=operation_number,
            sender=sender,
            receiver=receiver,
            organization=organization,
            fee=fee,
            notes=notes if notes else description  # Используем description как notes, если notes не указан
        )
    
    async def mark_receipt_as_read(self, receipt_id: int) -> bool:
        """Отметить чек как прочитанный администратором"""
        async with self.session_factory() as session:
            receipt = await session.get(Receipt, receipt_id)
            if not receipt:
                return False
            
            receipt.is_read = True
            await session.commit()
            return True
    
    async def get_unread_receipts_count(self, admin_id: int) -> int:
        """Получить количество непрочитанных чеков для администратора"""
        async with self.session_factory() as session:
            # Находим команду администратора
            team_query = select(Team).join(TeamMember).where(
                TeamMember.user_id == admin_id,
                TeamMember.is_admin == True
            )
            team_result = await session.execute(team_query)
            team = team_result.scalar_one_or_none()
            
            if not team:
                return 0
            
            # Получаем количество непрочитанных чеков
            query = select(func.count(Receipt.id)).where(
                Receipt.team_id == team.id,
                Receipt.is_read == False,
                Receipt.uploaded_by != admin_id  # Не считаем собственные чеки админа
            )
            result = await session.execute(query)
            return result.scalar_one()
