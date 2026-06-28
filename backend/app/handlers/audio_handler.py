import logging
import os
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.whatsapp_service import WhatsAppService
from app.services.message_service import MessageService

logger = logging.getLogger("audio_handler")
logger.setLevel(logging.INFO)

class AudioHandler:
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
        media_id = message.get("audio", {}).get("id")
        
        logger.info(f"--- Audio Message Received ---")
        logger.info(f"ID: {message_id}, Media ID: {media_id}")
        
        ws_srv = WhatsAppService()
        
        # 1. Save placeholder to DB with audio tag
        audio_url = f"/api/v1/portal/media/{message_id}"
        body = f'<audio controls src="{audio_url}"></audio>'
        
        await MessageService.save_message(
            db=db,
            clinic_id=clinic_id,
            sender=sender,
            recipient="Me",
            text=body,
            msg_type="audio",
            whatsapp_message_id=message_id,
            status="received",
            timestamp=timestamp
        )
        
        try:
            await ws_srv.send_read_receipt(sender, message_id)
            await ws_srv.send_typing_on(sender)
        except Exception as ws_err:
            logger.error(f"Failed to send typing/read status: {ws_err}")

        # Download media binary
        save_dir = os.path.join(os.getcwd(), "uploads", "audio")
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"{message_id}.ogg")
        
        media_url = await ws_srv.get_media_url(media_id)
        if media_url != "#":
            success = await ws_srv.download_media_file(media_url, file_path)
            if success:
                logger.info(f"Audio downloaded successfully to {file_path}")
                
                # 2. Extract Intent using Gemini
                if not bot_paused:
                    from app.services.booking_flow import BookingFlow
                    from app.services.llm_extractor import LLMExtractor
                    try:
                        intent_data = await LLMExtractor.extract_intent(text="", audio_path=file_path)
                        import json
                        payload = f"__AUDIO_INTENT__:{json.dumps(intent_data)}"
                        await BookingFlow.handle_message(
                            clinic_id=clinic_id,
                            phone_number=sender,
                            sender_name=profile_name,
                            msg_type="audio",
                            text_or_payload=payload,
                            db=db
                        )
                    except Exception as e:
                        logger.error(f"Failed to process audio with Gemini: {e}")
                        await BookingFlow.handle_message(
                            clinic_id=clinic_id,
                            phone_number=sender,
                            sender_name=profile_name,
                            msg_type="audio",
                            text_or_payload="[Audio extraction failed]",
                            db=db
                        )
                else:
                    logger.info(f"Bot is paused for {sender}. Skipping BookingFlow.")
            else:
                logger.error("Failed to download audio file.")
        else:
            logger.error("Failed to get media URL for audio.")
