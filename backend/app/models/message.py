from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.base import Base
from datetime import datetime

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    whatsapp_message_id = Column(String, unique=True, index=True, nullable=True)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    msg_type = Column(String, nullable=False)  # "text", "image", "audio", "video", "document", "interactive"
    status = Column(String, nullable=True)      # "sent", "delivered", "read", "failed", "received"
    timestamp = Column(DateTime, default=datetime.utcnow)
