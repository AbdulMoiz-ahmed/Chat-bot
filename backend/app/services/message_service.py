from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.message import Message
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger("message_service")
logger.setLevel(logging.INFO)

class MessageService:
    @staticmethod
    async def save_message(
        db: AsyncSession,
        sender: str,
        recipient: str,
        text: str,
        msg_type: str,
        clinic_id: int = None,
        whatsapp_message_id: Optional[str] = None,
        status: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Message:
        """
        Saves a WhatsApp message (incoming or outgoing) to the database.
        Prevents duplicates if whatsapp_message_id is provided and already exists.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        if whatsapp_message_id:
            stmt = select(Message).where(Message.whatsapp_message_id == whatsapp_message_id)
            result = await db.execute(stmt)
            existing = result.scalars().first()
            if existing:
                logger.info(f"Message with ID {whatsapp_message_id} already exists in database. Skipping insert.")
                return existing

        db_message = Message(
            clinic_id=clinic_id,
            sender=sender,
            recipient=recipient,
            text=text,
            msg_type=msg_type,
            whatsapp_message_id=whatsapp_message_id,
            status=status,
            timestamp=timestamp
        )
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)
        logger.info(f"Saved message to DB: ID {db_message.id}, Sender {sender}, Recipient {recipient}")
        
        # Broadcast message receipt via WebSocket manager
        try:
            from app.services.websocket_manager import manager
            await manager.broadcast("message_received", {
                "id": db_message.whatsapp_message_id or f"db_{db_message.id}",
                "sender": db_message.sender,
                "recipient": db_message.recipient,
                "text": db_message.text,
                "status": db_message.status,
                "timestamp": db_message.timestamp.isoformat()
            })
        except Exception as ws_err:
            logger.error(f"Failed to broadcast message_received WebSocket update: {ws_err}")

        return db_message

    @staticmethod
    async def get_messages(db: AsyncSession, limit: int = 100) -> List[Message]:
        """
        Retrieves recent messages from the database, ordered chronologically.
        """
        stmt = select(Message).order_by(Message.timestamp.asc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_message_status(
        db: AsyncSession,
        whatsapp_message_id: str,
        status: str
    ) -> bool:
        """
        Updates the delivery status of a message using its WhatsApp message ID (wamid).
        """
        stmt = (
            update(Message)
            .where(Message.whatsapp_message_id == whatsapp_message_id)
            .values(status=status)
        )
        result = await db.execute(stmt)
        await db.commit()
        updated = result.rowcount > 0
        if updated:
            logger.info(f"Updated status of message {whatsapp_message_id} to '{status}' in DB.")
            # Broadcast status update via WebSocket manager
            try:
                from app.services.websocket_manager import manager
                await manager.broadcast("message_status_updated", {
                    "whatsapp_message_id": whatsapp_message_id,
                    "status": status
                })
            except Exception as ws_err:
                logger.error(f"Failed to broadcast message_status_updated WebSocket update: {ws_err}")
        else:
            logger.warning(f"Could not find message {whatsapp_message_id} to update status to '{status}'.")
        return updated
