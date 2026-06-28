import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.message_service import MessageService

logger = logging.getLogger("interactive_handler")
logger.setLevel(logging.INFO)

class InteractiveHandler:
    """
    Handler for WhatsApp interactive messages (e.g. quick reply buttons, list selection).
    Logs the user's selections to the database.
    """
    @staticmethod
    async def handle(
        message: Dict[str, Any],
        db: AsyncSession,
        profile_name: str,
        timestamp: datetime = None,
        clinic_id: int = None,
        bot_paused: bool = False
    ):
        sender = message.get("from")
        message_id = message.get("id")
        interactive_data = message.get("interactive", {})
        interactive_type = interactive_data.get("type")
        
        logger.info(f"--- Interactive Message Received ---")
        logger.info(f"ID: {message_id}")
        logger.info(f"From: {sender}")
        logger.info(f"Type: {interactive_type}")
        
        body = ""
        payload_id = ""
        if interactive_type == "button_reply":
            button_reply = interactive_data.get("button_reply", {})
            btn_id = button_reply.get("id")
            btn_title = button_reply.get("title")
            logger.info(f"Button Reply ID: {btn_id}, Title: {btn_title}")
            body = f"[Button Clicked: {btn_title}]"
            payload_id = btn_id
            
        elif interactive_type == "list_reply":
            list_reply = interactive_data.get("list_reply", {})
            row_id = list_reply.get("id")
            row_title = list_reply.get("title")
            row_desc = list_reply.get("description")
            logger.info(f"List Reply ID: {row_id}, Title: {row_title}, Desc: {row_desc}")
            body = f"[List Selected: {row_title}]"
            payload_id = row_id
        else:
            body = f"[Interactive Reply: {interactive_type}]"
            
        # 1. Save interactive selections to database
        await MessageService.save_message(
            db=db,
            clinic_id=clinic_id,
            sender=sender,
            recipient="Me",
            text=body,
            msg_type="interactive",
            whatsapp_message_id=message_id,
            status="received",
            timestamp=timestamp
        )
        
        # Trigger read receipt (blue tick) and typing indicator
        try:
            from app.services.whatsapp_service import WhatsAppService
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
                msg_type="interactive",
                text_or_payload=payload_id,
                db=db
            )
        else:
            logger.info(f"Bot is paused for {sender}. Skipping BookingFlow.")
