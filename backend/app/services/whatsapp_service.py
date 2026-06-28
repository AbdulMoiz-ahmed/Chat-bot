import logging
import httpx
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger("whatsapp_service")
logger.setLevel(logging.INFO)

class WhatsAppService:
    """
    Service to handle WhatsApp Cloud API interactions, e.g. sending text messages.
    """
    def __init__(self, access_token: str = None, phone_number_id: str = None):
        self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        
    async def send_text_message(self, recipient_id: str, text: str) -> Dict[str, Any]:
        """
        Sends a simple text message via WhatsApp Cloud API.
        """
        if not self.access_token or not self.phone_number_id or self.access_token == "your_access_token_here" or self.phone_number_id == "your_phone_number_id_here":
            logger.warning("WhatsApp API credentials (token/phone number ID) are not configured. Logging echo response locally.")
            return {
                "status": "logged_locally",
                "recipient_id": recipient_id,
                "message": text
            }
            
        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {"body": text}
        }
        
        logger.info(f"Sending message to {recipient_id} via WhatsApp API...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response_data = response.json()
                if response.status_code >= 400:
                    logger.error(f"WhatsApp API error ({response.status_code}): {response_data}")
                    return {"status": "error", "error_data": response_data}
                logger.info(f"WhatsApp API success: {response_data}")
                return {"status": "sent", "api_response": response_data}
            except Exception as e:
                logger.error(f"Exception while sending message: {e}")
                return {"status": "exception", "error": str(e)}

    async def send_typing_on(self, recipient_id: str) -> None:
        """
        Sends a typing indicator status update to the recipient.
        """
        if not self.access_token or not self.phone_number_id or self.access_token == "your_access_token_here":
            return
        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "typing_indicator": {
                "type": "text"
            }
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code >= 400:
                    logger.error(f"Failed to trigger typing indicator: {response.text}")
            except Exception as e:
                logger.error(f"Failed to send typing indicator: {e}")

    async def send_read_receipt(self, recipient_id: str, message_id: str) -> None:
        """
        Sends a read status update (blue tick) for the received message.
        """
        if not self.access_token or not self.phone_number_id or self.access_token == "your_access_token_here":
            return
        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload, headers=headers)
            except Exception as e:
                logger.error(f"Failed to send read receipt: {e}")

    async def get_media_url(self, media_id: str) -> str:
        """
        Retrieves the direct download URL for a WhatsApp media item.
        """
        if not self.access_token or self.access_token == "your_access_token_here":
            logger.warning("WhatsApp access token is not configured. Returning fallback placeholder.")
            return "#"

        url = f"https://graph.facebook.com/v19.0/{media_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json().get("url", "#")
                else:
                    logger.error(f"Failed to get media URL from Meta ({response.status_code}): {response.text}")
                    return "#"
            except Exception as e:
                logger.error(f"Exception while retrieving media URL: {e}")
                return "#"

    async def send_interactive_buttons(self, recipient_id: str, text: str, buttons: list) -> Dict[str, Any]:
        """
        Sends an interactive message with up to 3 quick-reply buttons.
        buttons list format: [{"id": "btn_1", "title": "Button Title"}, ...]
        """
        if not self.access_token or not self.phone_number_id or self.access_token == "your_access_token_here":
            logger.warning("WhatsApp API credentials are not configured. Logging interactive buttons locally.")
            return {
                "status": "logged_locally",
                "recipient_id": recipient_id,
                "message": text,
                "buttons": buttons
            }

        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Build button elements
        formatted_buttons = []
        for btn in buttons[:3]:  # Max 3 buttons
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"]
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": formatted_buttons
                }
            }
        }

        logger.info(f"Sending interactive buttons to {recipient_id} via WhatsApp API...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response_data = response.json()
                if response.status_code >= 400:
                    logger.error(f"WhatsApp API interactive buttons error ({response.status_code}): {response_data}")
                    return {"status": "error", "error_data": response_data}
                logger.info(f"WhatsApp API interactive buttons success: {response_data}")
                return {"status": "sent", "api_response": response_data}
            except Exception as e:
                logger.error(f"Exception while sending interactive buttons: {e}")
                return {"status": "exception", "error": str(e)}

    async def send_interactive_list(
        self,
        recipient_id: str,
        text: str,
        button_label: str,
        sections: list,
        header: str = None,
        footer: str = None
    ) -> Dict[str, Any]:
        """
        Sends an interactive list message.
        sections format: [{"title": "Section Title", "rows": [{"id": "row_1", "title": "Row Title", "description": "Row description"}, ...]}]
        """
        if not self.access_token or not self.phone_number_id or self.access_token == "your_access_token_here":
            logger.warning("WhatsApp API credentials are not configured. Logging interactive list locally.")
            return {
                "status": "logged_locally",
                "recipient_id": recipient_id,
                "message": text,
                "sections": sections
            }

        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        interactive_data = {
            "type": "list",
            "body": {"text": text},
            "action": {
                "button": button_label[:20],  # Max 20 chars
                "sections": sections
            }
        }

        if header:
            interactive_data["header"] = {"type": "text", "text": header[:60]}  # Max 60 chars
        if footer:
            interactive_data["footer"] = {"text": footer[:60]}  # Max 60 chars

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "interactive",
            "interactive": interactive_data
        }

        logger.info(f"Sending interactive list to {recipient_id} via WhatsApp API...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response_data = response.json()
                if response.status_code >= 400:
                    logger.error(f"WhatsApp API interactive list error ({response.status_code}): {response_data}")
                    return {"status": "error", "error_data": response_data}
                logger.info(f"WhatsApp API interactive list success: {response_data}")
                return {"status": "sent", "api_response": response_data}
            except Exception as e:
                logger.error(f"Exception while sending interactive list: {e}")
                return {"status": "exception", "error": str(e)}
