import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.whatsapp_service import WhatsAppService
from app.services.message_service import MessageService

logger = logging.getLogger("text_handler")
logger.setLevel(logging.INFO)

class TextHandler:
    """
    Handler specifically for incoming WhatsApp text messages.
    Automatically echoes back received messages using WhatsAppService and logs both in DB.
    """
    @staticmethod
    async def handle(
        message: Dict[str, Any],
        db: AsyncSession,
        text_body: str,
        profile_name: str,
        timestamp: datetime = None,
        clinic_id: int = None,
        bot_paused: bool = False
    ):
        sender = message.get("from")
        message_id = message.get("id")
        
        logger.info(f"--- Text Message Received ---")
        logger.info(f"ID: {message_id}")
        logger.info(f"From: {sender}")
        logger.info(f"Body: {text_body}")
        
        # 1. Save incoming message to the database
        await MessageService.save_message(
            db=db,
            clinic_id=clinic_id,
            sender=sender,
            recipient="Me",
            text=text_body,
            msg_type="text",
            whatsapp_message_id=message_id,
            status="received",
            timestamp=timestamp
        )
        
        # Trigger read receipt (blue tick) and typing indicator
        try:
            ws_srv = WhatsAppService()
            await ws_srv.send_read_receipt(sender, message_id)
            await ws_srv.send_typing_on(sender)
        except Exception as ws_err:
            logger.error(f"Failed to send typing/read status: {ws_err}")
        
        # 2. Forward to state machine dialog manager
        if not bot_paused:
            from app.services.booking_flow import BookingFlow
            await BookingFlow.handle_message(
                clinic_id=clinic_id,
                phone_number=sender,
                sender_name=profile_name,
                msg_type="text",
                text_or_payload=text_body,
                db=db
            )
        else:
            logger.info(f"Bot is paused for {sender}. Skipping BookingFlow.")
