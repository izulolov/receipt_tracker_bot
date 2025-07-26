from datetime import datetime
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime  # Добавьте DateTime здесь
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
import secrets

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)

    members = relationship("TeamMember", back_populates="team")
    receipts = relationship("Receipt", back_populates="team")
    invites = relationship("TeamInvite", back_populates="team")

class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class TeamInvite(Base):
    __tablename__ = "team_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    team = relationship("Team", back_populates="invites")
    creator = relationship("User")
    
    @staticmethod
    def generate_code(length=8):
        """Generate a random invite code"""
        return secrets.token_hex(length // 2)
