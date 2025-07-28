from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from app.models.team import Team, TeamMember, TeamInvite
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
                # Проверяем, не состоит ли пользователь уже в какой-либо команде
                if await self.is_user_in_any_team(user_id):
                    raise ValueError("User is already a member of another team")
                    
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

    async def create_invite(
            self, 
            team_id: int, 
            creator_id: int, 
            expires_in_days: int = 7
    ) -> TeamInvite:
        """Create a new invite code for the team"""
        async with self.session_factory() as session:
            try:
                # Generate a unique code
                while True:
                    code = TeamInvite.generate_code()
                    # Check if code already exists
                    existing = await self.get_invite_by_code(code)
                    if not existing:
                        break
                
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
                
                invite = TeamInvite(
                    team_id=team_id,
                    code=code,
                    created_by=creator_id,
                    expires_at=expires_at
                )
                
                session.add(invite)
                await session.commit()
                await session.refresh(invite)
                return invite
            except Exception:
                await session.rollback()
                raise

    async def get_invite_by_code(self, code: str) -> Optional[TeamInvite]:
        """Get invite by code"""
        async with self.session_factory() as session:
            stmt = select(TeamInvite).where(TeamInvite.code == code)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def delete_invite(self, invite_id: int) -> bool:
        """Delete an invite"""
        async with self.session_factory() as session:
            try:
                stmt = select(TeamInvite).where(TeamInvite.id == invite_id)
                result = await session.execute(stmt)
                invite = result.scalars().first()
                
                if not invite:
                    return False
                    
                await session.delete(invite)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def get_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by id"""
        async with self.session_factory() as session:
            stmt = select(Team).where(Team.id == team_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def is_user_in_any_team(self, user_id: int) -> bool:
            """Проверяет, состоит ли пользователь в какой-либо команде"""
            async with self.session_factory() as session:
                stmt = select(TeamMember).where(TeamMember.user_id == user_id)
                result = await session.execute(stmt)
                return result.scalars().first() is not None
            
    async def count_team_admins(self, team_id: int) -> int:
        """Count the number of admins in a team"""
        async with self.session_factory() as session:
            stmt = select(TeamMember).where(
                and_(
                    TeamMember.team_id == team_id,
                    TeamMember.is_admin == True
                )
            )
            result = await session.execute(stmt)
            return len(result.scalars().all())

    async def remove_member(self, team_id: int, user_id: int) -> bool:
        """Remove a user from a team"""
        async with self.session_factory() as session:
            try:
                stmt = select(TeamMember).where(
                    and_(
                        TeamMember.team_id == team_id,
                        TeamMember.user_id == user_id
                    )
                )
                result = await session.execute(stmt)
                member = result.scalars().first()
                
                if not member:
                    return False
                    
                await session.delete(member)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def count_team_members(self, team_id: int) -> int:
        """Count total number of members in a team"""
        async with self.session_factory() as session:
            
            stmt = select(func.count()).select_from(TeamMember).where(
                TeamMember.team_id == team_id
            )
            result = await session.execute(stmt)
            return result.scalar_one() or 0