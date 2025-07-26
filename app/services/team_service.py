from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from app.models.team import Team, TeamInvite
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
            return False, "User not found. Please restart the bot with the /start command."

        # Check if team name already exists
        existing_team_by_name = await self.team_repository.get_by_name(team_name)
        if existing_team_by_name:
            return False, f"A team with the name '{team_name}' already exists. Please choose a different name."

        # Check if user already in any team
        if await self.team_repository.is_user_in_any_team(user.id):
            existing_team = await self.team_repository.get_user_team(user.id)
            return False, f"You are already a member of the team '{existing_team.name}'. Leave your current team first."

        try:
            team = await self.team_repository.create(name=team_name)
            await self.team_repository.add_member(
                team.id,
                user.id,
                is_admin=True
            )
            return True, f"Team '{team_name}' successfully created! You have been assigned as administrator."
        except Exception as e:
            return False, f"An error occurred while creating the team: {str(e)}"

    async def invite_member(
            self,
            admin_telegram_id: int,
            username: str
    ) -> Tuple[bool, str]:
        """Invite a user to team."""
        admin = await self.user_repository.get_by_telegram_id(
            admin_telegram_id)
        if not admin:
            return False, "Administrator not found"

        team = await self.team_repository.get_user_team(admin.id)
        if not team:
            return False, "You are not a member of any team"

        if not await self.team_repository.is_admin(team.id, admin.id):
            return False, "You are not a team administrator"

        user = await self.user_repository.get_by_username(username)
        if not user:
            return False, f"User @{username} not found"

        # Check if user already in any team
        if await self.team_repository.is_user_in_any_team(user.id):
            existing_team = await self.team_repository.get_user_team(user.id)
            return False, f"User is already a member of the team '{existing_team.name}'"

        try:
            await self.team_repository.add_member(
                team.id,
                user.id,
                is_admin=False
            )
            return True, f"User @{username} successfully invited to team '{team.name}'"
        except Exception as e:
            return False, f"Failed to invite user: {str(e)}"

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
    
    async def create_invite_link(
            self,
            admin_telegram_id: int,
            expires_in_days: int = 7
    ) -> Tuple[bool, str]:
        """Create an invite link for the team"""
        admin = await self.user_repository.get_by_telegram_id(admin_telegram_id)
        if not admin:
            return False, "Administrator not found"

        team = await self.team_repository.get_user_team(admin.id)
        if not team:
            return False, "You are not a member of any team"

        if not await self.team_repository.is_admin(team.id, admin.id):
            return False, "You are not a team administrator"

        try:
            invite = await self.team_repository.create_invite(
                team_id=team.id,
                creator_id=admin.id,
                expires_in_days=expires_in_days
            )
            
            # Generate invite code
            invite_code = invite.code
            
            return True, (f"Invite code for team '{team.name}' created:\n\n"
                        f"`{invite_code}`\n\n"
                        f"Code is valid for {expires_in_days} days.\n"
                        f"Users can join the team using the command:\n/join_team {invite_code}")
        except Exception as e:
            return False, f"Failed to create invite code: {str(e)}"

    async def join_team_by_code(
            self,
            telegram_id: int,
            invite_code: str
    ) -> Tuple[bool, str]:
        """Join a team using an invite code"""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return False, "User not found. Please restart the bot with the /start command."

        # Check if user already in any team
        if await self.team_repository.is_user_in_any_team(user.id):
            existing_team = await self.team_repository.get_user_team(user.id)
            return False, f"You are already a member of the team '{existing_team.name}'. Leave your current team first."

        # Get invite by code
        invite = await self.team_repository.get_invite_by_code(invite_code)
        if not invite:
            return False, "Invalid invite code. Please check the code and try again."

        # Check if invite has expired
        if invite.expires_at and invite.expires_at < datetime.utcnow():
            return False, "The invite code has expired. Please request a new code."

        try:
            # Get team
            team = await self.team_repository.get_by_id(invite.team_id)
            if not team:
                return False, "Team not found. It may have been deleted."

            # Add user to team
            await self.team_repository.add_member(
                team.id,
                user.id,
                is_admin=False
            )
            
            return True, f"You have successfully joined the team '{team.name}'!"
        except ValueError as e:
            return False, str(e)  # Ловим ошибку из add_member
        except Exception as e:
            return False, f"Failed to join the team: {str(e)}"

    async def leave_team(
            self,
            telegram_id: int
    ) -> Tuple[bool, str]:
        """Leave current team"""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return False, "User not found. Please restart the bot with the /start command."

        # Check if user is in a team
        team = await self.team_repository.get_user_team(user.id)
        if not team:
            return False, "You are not a member of any team."

        # Check if user is the only admin
        is_admin = await self.team_repository.is_admin(team.id, user.id)
        if is_admin:
            # Count admins in team
            admin_count = await self.team_repository.count_team_admins(team.id)
            if admin_count <= 1:
                return False, "You are the only administrator of the team. Please assign another administrator before leaving."

        try:
            success = await self.team_repository.remove_member(team.id, user.id)
            if success:
                return True, f"You have successfully left the team '{team.name}'."
            return False, "Failed to leave the team."
        except Exception as e:
            return False, f"An error occurred: {str(e)}"
        
    async def leave_team(
            self,
            telegram_id: int
    ) -> Tuple[bool, str]:
        """Leave current team"""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return False, "User not found. Please restart the bot with the /start command."

        # Check if user is in a team
        team = await self.team_repository.get_user_team(user.id)
        if not team:
            return False, "You are not a member of any team."

        # Check if user is the only admin
        is_admin = await self.team_repository.is_admin(team.id, user.id)
        if is_admin:
            # Count admins in team
            admin_count = await self.team_repository.count_team_admins(team.id)
            if admin_count <= 1:
                return False, "You are the only administrator of the team. Please assign another administrator before leaving."

        try:
            success = await self.team_repository.remove_member(team.id, user.id)
            if success:
                return True, f"You have successfully left the team '{team.name}'."
            return False, "Failed to leave the team."
        except Exception as e:
            return False, f"An error occurred: {str(e)}"