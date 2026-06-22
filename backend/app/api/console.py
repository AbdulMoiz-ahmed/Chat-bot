from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.config import settings
from app.db.session import get_db
from app.services.whatsapp_service import WhatsAppService
from app.services.message_service import MessageService
import os

router = APIRouter()

# Locate templates directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_dir = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)

class SendMessageRequest(BaseModel):
    number: str
    text: str

@router.get("/", response_class=HTMLResponse)
async def serve_console(request: Request):
    """
    Serves the premium WhatsApp Chat Console.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "phone_number_id": settings.WHATSAPP_PHONE_NUMBER_ID,
            "verify_token": settings.WHATSAPP_VERIFY_TOKEN
        }
    )

@router.get("/messages")
async def get_messages(db: AsyncSession = Depends(get_db)):
    """
    Returns the recent messages history log from the database.
    """
    db_messages = await MessageService.get_messages(db, limit=100)
    messages_payload = []
    for msg in db_messages:
        messages_payload.append({
            "id": msg.whatsapp_message_id or f"db_{msg.id}",
            "sender": msg.sender,
            "recipient": msg.recipient,
            "text": msg.text,
            "status": msg.status,
            "timestamp": msg.timestamp.isoformat()
        })
    return messages_payload

@router.post("/send")
async def send_message(req: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Sends a WhatsApp message via WhatsApp Cloud API and persists it to the database.
    """
    number = req.number.strip()
    if number.startswith("+"):
        number = number[1:]
        
    text = req.text.strip()
    
    if not number or not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number and message text are required"
        )
        
    whatsapp_service = WhatsAppService()
    result = await whatsapp_service.send_text_message(number, text)
    
    if result.get("status") in ("sent", "logged_locally"):
        api_resp = result.get("api_response", {})
        msg_id = None
        if "messages" in api_resp and len(api_resp["messages"]) > 0:
            msg_id = api_resp["messages"][0].get("id")
            
        # Log to DB
        db_message = await MessageService.save_message(
            db=db,
            clinic_id=1,
            sender="Me (You)",
            recipient=number,
            text=text,
            msg_type="text",
            whatsapp_message_id=msg_id,
            status="sent"
        )
        
        return {
            "success": True,
            "message": {
                "id": db_message.whatsapp_message_id or f"db_{db_message.id}",
                "sender": db_message.sender,
                "recipient": db_message.recipient,
                "text": db_message.text,
                "status": db_message.status,
                "timestamp": db_message.timestamp.isoformat()
            }
        }
    else:
        error_msg = result.get("error_data", {}).get("error", {}).get("message", "WhatsApp API execution failed")
        return {
            "success": False,
            "error": error_msg
        }
