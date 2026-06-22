import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.message_service import MessageService

logger = logging.getLogger("status_handler")
logger.setLevel(logging.INFO)

class StatusHandler:
    """
    Handler for message status updates (sent, delivered, read, failed).
    Updates message status in the database.
    """
    @staticmethod
    async def handle(status: Dict[str, Any], db: AsyncSession, clinic_id: int = None):
        status_value = status.get("status")
        message_id = status.get("id")
        recipient = status.get("recipient_id")
        
        logger.info(f"--- Status Update Callback ---")
        logger.info(f"Message ID: {message_id}")
        logger.info(f"Recipient: {recipient}")
        logger.info(f"Status: {status_value}")
        
        if status_value == "failed":
            errors = status.get("errors", [])
            for error in errors:
                err_code = error.get("code")
                err_msg = error.get("message")
                logger.error(f"Status Error Code {err_code}: {err_msg}")
                
        # Update message status in database
        await MessageService.update_message_status(
            db=db,
            whatsapp_message_id=message_id,
            status=status_value
        )
