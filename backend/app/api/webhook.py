import logging
from fastapi import APIRouter, Request, Query, Response, status, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.services.signature_service import SignatureService
from app.services.message_router import MessageRouter

logger = logging.getLogger("webhook")
logger.setLevel(logging.INFO)

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """
    GET endpoint for WhatsApp Webhook verification handshake.
    Validates the mode and verification token, and returns the challenge.
    """
    logger.info(f"Received webhook verification handshake request.")
    logger.info(f"hub.mode: {hub_mode}")
    logger.info(f"hub.verify_token: {hub_verify_token}")
    logger.info(f"hub.challenge: {hub_challenge}")

    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Handshake token verified successfully. Returning challenge.")
        # Return challenge as plain text with 200 OK
        return Response(content=hub_challenge, media_type="text/plain")
    else:
        logger.warning("Handshake verification failed: Token mismatch or invalid mode.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification token mismatch or invalid mode."
        )

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db)
):
    """
    POST endpoint to receive and process webhook notifications from WhatsApp.
    Ensures message security by validating HMAC-SHA256 signature using APP_SECRET.
    """
    # Read raw body bytes for signature validation
    body_bytes = await request.body()
    
    # Verify the HMAC SHA256 signature using the WhatsApp App Secret
    if not SignatureService.verify_signature(
        body_bytes, x_hub_signature_256, settings.WHATSAPP_APP_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature verification failed."
        )
        
    # Parse body payload as JSON
    try:
        payload = await request.json()
    except Exception:
        logger.error("Failed to parse incoming payload as JSON.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format."
        )
        
    logger.info("Incoming WhatsApp message accepted. Routing payload...")
    
    # Process the routed messages asynchronously with the database session
    await MessageRouter.route(payload, db)
    
    # Return 200 OK to WhatsApp API to confirm receipt
    return {"status": "success"}
