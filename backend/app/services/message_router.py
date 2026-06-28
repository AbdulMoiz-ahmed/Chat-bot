import logging
from typing import Dict, Any
from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.clinic import Clinic
from app.handlers.text_handler import TextHandler
from app.handlers.interactive_handler import InteractiveHandler
from app.handlers.status_handler import StatusHandler
from app.handlers.audio_handler import AudioHandler
from app.services.whatsapp_service import WhatsAppService
from app.services.message_service import MessageService
from app.services.session_service import SessionService

logger = logging.getLogger("message_router")
logger.setLevel(logging.INFO)

class MessageRouter:
    """
    Parses the Facebook/Meta Webhook structure and dispatches objects to
    their specific handler classes, persisting all interactions in the database.
    """
    @staticmethod
    async def route(payload: Dict[str, Any], db: AsyncSession):
        # Verify it's from a WhatsApp subscription field
        if payload.get("object") != "whatsapp_business_account":
            logger.warning(f"Unexpected webhook object type: {payload.get('object')}")
            return
            
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                
                # Extract phone_number_id to route to the correct clinic
                phone_number_id = value.get("metadata", {}).get("phone_number_id")
                if not phone_number_id:
                    continue
                    
                stmt = select(Clinic).where(Clinic.wa_phone_number_id == phone_number_id)
                res = await db.execute(stmt)
                clinic = res.scalars().first()
                
                if not clinic:
                    logger.warning(f"No clinic found for phone_number_id: {phone_number_id}")
                    continue
                    
                clinic_id = clinic.id
                
                # 1. Process Messages (Incoming from users)
                messages = value.get("messages", [])
                for message in messages:
                    sender = message.get("from")
                    msg_id = message.get("id")
                    msg_type = message.get("type")
                    timestamp_unix = message.get("timestamp")
                    
                    # Convert unix timestamp string to datetime if available
                    timestamp = None
                    if timestamp_unix:
                        try:
                            timestamp = datetime.utcfromtimestamp(int(timestamp_unix))
                        except Exception as e:
                            logger.error(f"Error parsing timestamp {timestamp_unix}: {e}")
                    
                    # Extract sender profile name from contacts list
                    contacts = value.get("contacts", [])
                    profile_name = "Patient"
                    if contacts:
                        profile_name = contacts[0].get("profile", {}).get("name", "Patient")

                    session = await SessionService.get_session(sender, clinic_id)
                    bot_paused = session.get("bot_paused", False)

                    if msg_type == "text":
                        body = message.get("text", {}).get("body", "")
                        await TextHandler.handle(message, db, body, profile_name, timestamp, clinic_id, bot_paused)
                    elif msg_type == "interactive":
                        await InteractiveHandler.handle(message, db, profile_name, timestamp, clinic_id, bot_paused)
                    elif msg_type == "audio":
                        import asyncio
                        # Process audio in the background since it requires downloading
                        asyncio.create_task(AudioHandler.handle(message, db, profile_name, timestamp, clinic_id, bot_paused))
                    else:
                        # Handle other media types and store them directly
                        body = ""
                        if msg_type == "image":
                            media_id = message.get("image", {}).get("id")
                            whatsapp_service = WhatsAppService()
                            media_url = await whatsapp_service.get_media_url(media_id)
                            body = f'<img src="{media_url}" alt="Image" class="chat-image" />'
                        elif msg_type == "video":
                            body = "[🎥 Video Received]"
                        elif msg_type == "document":
                            body = "[📄 Document Received]"
                        else:
                            body = f"[📦 {msg_type.capitalize() if msg_type else 'Unknown'} Received]"
                            
                        logger.info(f"Received media message '{msg_type}'. Body formatted. Saving to DB...")
                        await MessageService.save_message(
                            db=db,
                            clinic_id=clinic_id,
                            sender=sender,
                            recipient="Me",
                            text=body,
                            msg_type=msg_type or "unknown",
                            whatsapp_message_id=msg_id,
                            status="received",
                            timestamp=timestamp
                        )
                
                # 2. Process Status Updates (Sent, Delivered, Read, Failed notifications)
                statuses = value.get("statuses", [])
                for status in statuses:
                    await StatusHandler.handle(status, db, clinic_id)
