from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, and_
from app.models.team import Team, TeamMember
from app.models.receipt import Receipt
from .base import BaseRepository


class TeamRepository(BaseRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.model = Team

    async def get_user_team(self, user_id: int) -> Optional[Team]:
        async with self.session_factory() as session:
            stmt = (
                select(Team)
                .join(TeamMember)
                .where(TeamMember.user_id == user_id)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def is_admin(self, team_id: int, user_id: int) -> bool:
        async with self.session_factory() as session:
            stmt = select(TeamMember).where(
                and_(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user_id,
                    TeamMember.is_admin == True
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first() is not None

    async def add_member(
            self,
            team_id: int,
            user_id: int,
            is_admin: bool = False
    ) -> TeamMember:
        async with self.session_factory() as session:
            try:
                team_member = TeamMember(
                    team_id=team_id,
                    user_id=user_id,
                    is_admin=is_admin
                )
                session.add(team_member)
                await session.commit()
                await session.refresh(team_member)
                return team_member
            except Exception:
                await session.rollback()
                raise

    async def get_team_receipts(
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

    async def get_by_name(self, team_name: str) -> Optional[Team]:
        """Получить команду по имени"""
        async with self.session_factory() as session:
            stmt = select(Team).where(Team.name == team_name)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def create(self, name: str) -> Team:
        """Создать новую команду"""
        async with self.session_factory() as session:
            try:
                team = Team(name=name)
                session.add(team)
                await session.commit()
                await session.refresh(team)
                return team
            except Exception:
                await session.rollback()
                raise
