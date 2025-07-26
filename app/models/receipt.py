from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey,
    DateTime, Numeric, Boolean
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class Receipt(Base):
    __tablename__ = 'receipts'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'))
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    date = Column(DateTime)
    amount = Column(Numeric(10, 2))
    operation_number = Column(String)
    sender = Column(String)
    receiver = Column(String)
    status = Column(String)
    file_path = Column(String)
    creation_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    notes = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    fee = Column(Numeric(10, 2), nullable=True)
    is_read = Column(Boolean, default=False)  # Новое поле для отслеживания прочитанных чеков

    # Relationships
    team = relationship("Team", back_populates="receipts")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return (
            f"<Receipt("
            f"id={self.id}, "
            f"amount={self.amount}, "
            f"operation_number={self.operation_number}"
            f")>"
        )