from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base

class NlpLog(Base):
    __tablename__ = "nlp_logs"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=True)
    patient_phone = Column(String(50), nullable=False)
    raw_message = Column(Text, nullable=False)
    llm_response = Column(Text, nullable=True)
    error_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed = Column(Boolean, default=False)
