from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    wa_phone_number_id = Column(String, unique=True, index=True, nullable=False)
    timezone = Column(String, default="UTC", nullable=False)
    language = Column(String, default="en", nullable=False)
    address = Column(String, nullable=True)
    working_hours = Column(String, nullable=True)
    general_info = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Clinic(id={self.id}, name='{self.name}', wa_phone_number_id='{self.wa_phone_number_id}')>"
