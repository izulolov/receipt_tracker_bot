from typing import Optional, List, Tuple
from datetime import datetime
from app.models.team import Team
from app.models.receipt import Receipt
from app.repositories.team import TeamRepository
from app.repositories.user import UserRepository
from .base import BaseService


class TeamService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self.team_repository = TeamRepository(session)
        self.user_repository = UserRepository(session)

    async def create_team(
            self,
            telegram_id: int,
            team_name: str
    ) -> Tuple[bool, str]:
        """Create a new team and add creator as admin."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return False, "Пользователь не найден. Пожалуйста, перезапустите бота командой /start."

        # Check if team name already exists
        existing_team_by_name = await self.team_repository.get_by_name(team_name)
        if existing_team_by_name:
            return False, f"Команда с названием '{team_name}' уже существует. Пожалуйста, выберите другое название."

        # Check if user already in team
        existing_team = await self.team_repository.get_user_team(user.id)
        if existing_team:
            return False, f"Вы уже состоите в команде '{existing_team.name}'. Сначала покиньте текущую команду."

        try:
            team = await self.team_repository.create(name=team_name)
            await self.team_repository.add_member(
                team.id,
                user.id,
                is_admin=True
            )
            return True, f"Команда '{team_name}' успешно создана! Вы назначены администратором."
        except Exception as e:
            return False, f"Произошла ошибка при создании команды: {str(e)}"

    async def invite_member(
            self,
            admin_telegram_id: int,
            username: str
    ) -> Tuple[bool, str]:
        """Invite a user to team."""
        admin = await self.user_repository.get_by_telegram_id(
            admin_telegram_id)
        if not admin:
            return False, "Администратор не найден"

        team = await self.team_repository.get_user_team(admin.id)
        if not team:
            return False, "Вы не состоите ни в одной команде"

        if not await self.team_repository.is_admin(team.id, admin.id):
            return False, "Вы не являетесь администратором команды"

        user = await self.user_repository.get_by_username(username)
        if not user:
            return False, f"Пользователь @{username} не найден"

        # Check if user already in a team
        existing_team = await self.team_repository.get_user_team(user.id)
        if existing_team:
            return False, f"Пользователь уже состоит в команде '{existing_team.name}'"

        try:
            await self.team_repository.add_member(
                team.id,
                user.id,
                is_admin=False
            )
            return True, f"Пользователь @{username} успешно приглашен в команду '{team.name}'"
        except Exception as e:
            return False, f"Не удалось пригласить пользователя: {str(e)}"

    async def get_user_team(
            self,
            telegram_id: int
    ) -> Optional[Team]:
        """Get user's team."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return None
        return await self.team_repository.get_user_team(user.id)

    async def get_team_receipts(
            self,
            team_id: int,
            start_date: datetime,
            end_date: datetime
    ) -> List[Receipt]:
        """Get team receipts for date range."""
        return await self.team_repository.get_team_receipts(
            team_id,
            start_date,
            end_date
        )

    async def is_team_admin(
            self,
            telegram_id: int,
            team_id: int
    ) -> bool:
        """Check if user is team admin."""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return False
        return await self.team_repository.is_admin(team_id, user.id)