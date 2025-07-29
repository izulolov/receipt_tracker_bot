from sqlalchemy import Column, Integer, String, BigInteger
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.team import TeamMember as team_members


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    username = Column(String)

    # Relationships
    #teams = relationship(
    #    "Team",
    #    secondary=team_members,
    #    back_populates="members"
    #)

    # Возможно это решение временное. Разберемся потом
    team_memberships = relationship("TeamMember", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"