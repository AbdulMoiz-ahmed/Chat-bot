import asyncio
import hashlib
import hmac
import json
import logging
from httpx import AsyncClient, ASGITransport

# Configure logging to see the server behavior during test execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_roundtrip")

from app.main import app
from app.core.config import settings

async def run_verification():
    logger.info("Starting webhook roundtrip verification...")
    
    # We will use httpx.AsyncClient directly with the FastAPI app instance
    # This allows testing the endpoints without needing to run a separate server process.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        
        # 1. Verify Webhook GET Handshake
        logger.info("\n--- 1. Testing GET Webhook Verification Handshake ---")
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
            "hub.challenge": "handshake_challenge_12345"
        }
        
        verify_response = await client.get("/api/v1/webhook", params=params)
        logger.info(f"Handshake GET Response Status: {verify_response.status_code}")
        logger.info(f"Handshake GET Response Content: {verify_response.text}")
        
        assert verify_response.status_code == 200, "Verification handshake failed!"
        assert verify_response.text == "handshake_challenge_12345", "Verification challenge mismatch!"
        logger.info("GET Handshake verified successfully!")

        # 2. Verify Webhook POST Echo Message Routing
        logger.info("\n--- 2. Testing POST Webhook Echo Bot Routing ---")
        
        # WhatsApp Mock message payload
        mock_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "10987654321",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "16505551111",
                                    "phone_number_id": "1234567890"
                                },
                                "contacts": [
                                    {
                                        "profile": {
                                            "name": "Jane Doe"
                                        },
                                        "wa_id": "1234567890"
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "+1234567890",
                                        "id": "wamid.HBgLMTIzNDU2Nzg5MFVAChJBOTk5RjQyRDZDRDY2NzZDRTkA",
                                        "timestamp": "1603222396",
                                        "text": {
                                            "body": "Hello Antigravity!"
                                        },
                                        "type": "text"
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        
        body_bytes = json.dumps(mock_payload).encode("utf-8")
        
        # Generate SHA256 signature using the app secret
        signature = hmac.new(
            settings.WHATSAPP_APP_SECRET.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-Hub-Signature-256": f"sha256={signature}",
            "Content-Type": "application/json"
        }
        
        # Send the mock message request to the webhook
        response = await client.post("/api/v1/webhook", content=body_bytes, headers=headers)
        logger.info(f"POST Message Response Status: {response.status_code}")
        logger.info(f"POST Message Response Content: {response.json()}")
        
        assert response.status_code == 200, "POST webhook call failed!"
        assert response.json().get("status") == "success", "Failed processing webhook!"
        
        logger.info("\nWebhook POST Message processing and routing succeeded!")
        logger.info("Roundtrip echo bot verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_verification())
