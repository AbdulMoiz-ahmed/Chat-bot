from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, timedelta
import logging

from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.timeslot import TimeSlot
from app.models.clinic import Clinic
from app.models.appointment import Appointment
from app.models.message import Message
from app.api.deps import get_db, get_current_user
from app.services.websocket_manager import manager
from app.core.config import settings
import jwt
from app.services.whatsapp_service import WhatsAppService
from app.services.message_service import MessageService
from app.api.deps import get_current_user
from app.models.user import User
from app.models.nlp_log import NlpLog

logger = logging.getLogger("console_api")
router = APIRouter()

# --- Pydantic Models ---
class DoctorCreate(BaseModel):
    name: str
    specialty: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None

class DoctorResponse(BaseModel):
    id: int
    name: str
    specialty: str
    email: Optional[str]
    phone_number: Optional[str]
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ClinicSettingsUpdate(BaseModel):
    address: Optional[str] = None
    working_hours: Optional[str] = None
    general_info: Optional[str] = None

class ClinicSettingsResponse(BaseModel):
    id: int
    name: str
    address: Optional[str]
    working_hours: Optional[str]
    general_info: Optional[str]

    class Config:
        from_attributes = True

class TimeSlotCreate(BaseModel):
    doctor_id: int
    start_time: datetime
    end_time: datetime

class TimeSlotResponse(BaseModel):
    id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    is_available: bool
    is_blocked: bool
    appointment: Optional[dict] = None

    class Config:
        from_attributes = True

class BlockTimeSlotRequest(BaseModel):
    timeslot_id: int
    is_blocked: bool

class SendMessageRequest(BaseModel):
    phone_number: str
    text: str

# --- Clinic Settings Endpoints ---

@router.get("/portal/clinics/settings", response_model=ClinicSettingsResponse)
async def get_clinic_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Must belong to a clinic")
        
    result = await db.execute(select(Clinic).where(Clinic.id == current_user.clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
        
    return clinic

@router.put("/portal/clinics/settings", response_model=ClinicSettingsResponse)
async def update_clinic_settings(
    req: ClinicSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Must belong to a clinic")
        
    result = await db.execute(select(Clinic).where(Clinic.id == current_user.clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
        
    if req.address is not None:
        clinic.address = req.address
    if req.working_hours is not None:
        clinic.working_hours = req.working_hours
    if req.general_info is not None:
        clinic.general_info = req.general_info
        
    await db.commit()
    await db.refresh(clinic)
    return clinic

# --- Doctor Endpoints ---

@router.get("/portal/doctors", response_model=List[DoctorResponse])
async def get_doctors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Doctor)
    if current_user.clinic_id is not None:
        query = query.where(Doctor.clinic_id == current_user.clinic_id)
    result = await db.execute(query.order_by(Doctor.name))
    return result.scalars().all()

@router.post("/portal/doctors", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    req: DoctorCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Must belong to a clinic to create a doctor")
        
    doctor = Doctor(
        clinic_id=current_user.clinic_id,
        name=req.name,
        specialty=req.specialty,
        email=req.email,
        phone_number=req.phone_number,
        bio=req.bio
    )
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)
    return doctor

@router.put("/portal/doctors/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(doctor_id: int, req: DoctorCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    doctor.name = req.name
    doctor.specialty = req.specialty
    doctor.email = req.email
    doctor.phone_number = req.phone_number
    if req.bio is not None:
        doctor.bio = req.bio
    
    await db.commit()
    await db.refresh(doctor)
    return doctor

@router.delete("/portal/doctors/{doctor_id}")
async def delete_doctor(doctor_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    await db.delete(doctor)
    await db.commit()
    return {"success": True}

# --- TimeSlot & Calendar Endpoints ---

@router.get("/portal/timeslots")
async def get_timeslots(
    doctor_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(TimeSlot)
    conditions = []
    
    if current_user.clinic_id is not None:
        conditions.append(TimeSlot.clinic_id == current_user.clinic_id)
    
    if doctor_id:
        conditions.append(TimeSlot.doctor_id == doctor_id)
    
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        conditions.append(TimeSlot.start_time >= start_dt)
        
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        conditions.append(TimeSlot.start_time <= end_dt)
    elif start_date:
        # If only start_date is provided, default to just that day
        end_dt = datetime.combine(start_date, datetime.max.time())
        conditions.append(TimeSlot.start_time <= end_dt)
        
    if conditions:
        query = query.where(and_(*conditions))
        
    query = query.order_by(TimeSlot.start_time)
    result = await db.execute(query)
    slots = result.scalars().all()
    
    # We want to attach appointment details if the slot is booked
    payload = []
    for slot in slots:
        slot_dict = {
            "id": slot.id,
            "doctor_id": slot.doctor_id,
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
            "is_available": slot.is_available,
            "is_blocked": slot.is_blocked,
            "appointment": None
        }
        
        # Query appointment if not available and not blocked
        if not slot.is_available and not slot.is_blocked:
            app_result = await db.execute(
                select(Appointment, Patient)
                .join(Patient, Appointment.patient_id == Patient.id)
                .where(Appointment.timeslot_id == slot.id)
            )
            app_data = app_result.first()
            if app_data:
                appt, pat = app_data
                slot_dict["appointment"] = {
                    "id": appt.id,
                    "status": appt.status,
                    "patient": {
                        "id": pat.id,
                        "name": pat.name,
                        "phone_number": pat.phone_number
                    }
                }
        payload.append(slot_dict)
        
    return payload

@router.post("/portal/timeslots", status_code=status.HTTP_201_CREATED)
async def create_timeslot(
    req: TimeSlotCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Must belong to a clinic to create a timeslot")
        
    # Check if doctor exists and belongs to clinic
    doc_res = await db.execute(select(Doctor).where(
        and_(Doctor.id == req.doctor_id, Doctor.clinic_id == current_user.clinic_id)
    ))
    if not doc_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Doctor not found in your clinic")
        
    slot = TimeSlot(
        clinic_id=current_user.clinic_id,
        doctor_id=req.doctor_id,
        start_time=req.start_time,
        end_time=req.end_time,
        is_available=True,
        is_blocked=False
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    
    # Broadcast timeslot update
    await manager.broadcast("timeslot_created", {
        "id": slot.id,
        "doctor_id": slot.doctor_id,
        "start_time": slot.start_time.isoformat(),
        "end_time": slot.end_time.isoformat(),
        "is_available": slot.is_available,
        "is_blocked": slot.is_blocked
    })
    
    return slot

@router.post("/portal/timeslots/block")
async def block_timeslot(req: BlockTimeSlotRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(TimeSlot).where(TimeSlot.id == req.timeslot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
        
    slot.is_blocked = req.is_blocked
    # If blocked, it is not available. If unblocked, it is available (unless an appointment exists)
    if slot.is_blocked:
        slot.is_available = False
    else:
        # Check if there's any active appointment
        appt_res = await db.execute(select(Appointment).where(Appointment.timeslot_id == slot.id))
        appt = appt_res.scalar_one_or_none()
        if appt and appt.status not in ("canceled", "no_show"):
            slot.is_available = False
        else:
            slot.is_available = True
            
    await db.commit()
    await db.refresh(slot)
    
    # Broadcast timeslot block change
    await manager.broadcast("timeslot_updated", {
        "id": slot.id,
        "doctor_id": slot.doctor_id,
        "start_time": slot.start_time.isoformat(),
        "end_time": slot.end_time.isoformat(),
        "is_available": slot.is_available,
        "is_blocked": slot.is_blocked
    })
    
    return {"success": True, "timeslot": {
        "id": slot.id,
        "is_available": slot.is_available,
        "is_blocked": slot.is_blocked
    }}

# --- Conversations Endpoints (phone-number based, not patient-dependent) ---

class SaveContactNameRequest(BaseModel):
    name: str

@router.get("/portal/conversations")
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Build conversation threads from the messages table.
    Groups messages by phone number (the non-'Me (You)' party),
    returns each thread with the contact's name (from patients table if exists),
    last message preview, and unread count.
    """
    # Get all messages for this clinic
    query = select(Message)
    if current_user.clinic_id is not None:
        query = query.where(Message.clinic_id == current_user.clinic_id)
    result = await db.execute(query.order_by(Message.timestamp.asc()))
    all_messages = result.scalars().all()

    # Group messages by the other party's phone number
    threads: dict = {}  # phone_number -> { messages, last_message, ... }
    for msg in all_messages:
        # Determine the other party's phone number
        if msg.sender == "Me (You)":
            phone = msg.recipient
        else:
            phone = msg.sender
        
        if not phone:
            continue
        
        # Normalize phone
        clean_phone = phone.replace("+", "").strip()
        if not clean_phone:
            continue

        if clean_phone not in threads:
            threads[clean_phone] = {
                "phone_number": clean_phone,
                "messages": [],
                "last_message": None,
                "unread_count": 0,
            }
        
        threads[clean_phone]["messages"].append(msg)
        threads[clean_phone]["last_message"] = msg
        # Count incoming messages that aren't read
        if msg.sender != "Me (You)" and msg.status not in ("read",):
            threads[clean_phone]["unread_count"] += 1

    # Now look up patient names for each phone number
    conversations = []
    for phone, thread_data in threads.items():
        # Try to find patient record with matching phone
        patient_result = await db.execute(
            select(Patient).where(
                or_(
                    Patient.phone_number.like(f"%{phone}%"),
                    Patient.phone_number.like(f"%{phone[-10:]}%") if len(phone) >= 10 else Patient.phone_number.like(f"%{phone}%")
                )
            ).limit(1)
        )
        patient = patient_result.scalars().first()
        
        last_msg = thread_data["last_message"]
        conversations.append({
            "phone_number": phone,
            "name": patient.name if patient else None,
            "patient_id": patient.id if patient else None,
            "last_message": {
                "text": last_msg.text if last_msg else None,
                "timestamp": last_msg.timestamp.isoformat() if last_msg else None,
                "status": last_msg.status if last_msg else None,
                "sender": last_msg.sender if last_msg else None,
            } if last_msg else None,
            "unread_count": thread_data["unread_count"],
            "message_count": len(thread_data["messages"]),
        })
    
    # Sort by last message timestamp (newest first)
    conversations.sort(
        key=lambda c: c["last_message"]["timestamp"] if c.get("last_message") and c["last_message"].get("timestamp") else "",
        reverse=True
    )
    
    return conversations


@router.get("/portal/conversations/{phone}/messages")
async def get_conversation_messages(
    phone: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all messages for a specific phone number conversation."""
    clean_phone = phone.replace("+", "").strip()
    
    query = select(Message).where(
        or_(
            Message.sender.like(f"%{clean_phone}%"),
            Message.recipient.like(f"%{clean_phone}%")
        )
    )
    if current_user.clinic_id is not None:
        query = query.where(Message.clinic_id == current_user.clinic_id)
    
    result = await db.execute(query.order_by(Message.timestamp.asc()))
    messages = result.scalars().all()
    
    return [
        {
            "id": msg.whatsapp_message_id or f"db_{msg.id}",
            "sender": msg.sender,
            "recipient": msg.recipient,
            "text": msg.text,
            "status": msg.status,
            "timestamp": msg.timestamp.isoformat(),
            "msg_type": msg.msg_type,
        }
        for msg in messages
    ]


@router.put("/portal/conversations/{phone}/name")
async def save_contact_name(
    phone: str,
    req: SaveContactNameRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save or update contact name. If patient exists, update their name. Otherwise create a new patient record."""
    clean_phone = phone.replace("+", "").strip()
    new_name = req.name.strip()
    
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    
    # Resolve clinic_id
    clinic_id = current_user.clinic_id
    if clinic_id is None:
        from app.models.clinic import Clinic
        result = await db.execute(select(Clinic).limit(1))
        first_clinic = result.scalars().first()
        if first_clinic:
            clinic_id = first_clinic.id
        else:
            raise HTTPException(status_code=400, detail="No clinic found")
    
    # Check if patient already exists with this phone number
    patient_result = await db.execute(
        select(Patient).where(
            or_(
                Patient.phone_number == clean_phone,
                Patient.phone_number == f"+{clean_phone}",
                Patient.phone_number.like(f"%{clean_phone}%")
            )
        ).limit(1)
    )
    patient = patient_result.scalars().first()
    
    if patient:
        patient.name = new_name
        await db.commit()
        await db.refresh(patient)
        return {"success": True, "message": "Contact name updated", "patient_id": patient.id, "name": patient.name}
    else:
        # Create new patient record
        new_patient = Patient(
            clinic_id=clinic_id,
            name=new_name,
            phone_number=clean_phone,
        )
        db.add(new_patient)
        await db.commit()
        await db.refresh(new_patient)
        return {"success": True, "message": "Contact created", "patient_id": new_patient.id, "name": new_patient.name}

# --- Media and Audio Endpoints ---

from fastapi.responses import FileResponse
import os

@router.get("/portal/media/{message_id}")
async def get_media(
    message_id: str,
    current_user: User = Depends(get_current_user)
):
    save_dir = os.path.join(os.getcwd(), "uploads", "audio")
    file_path = os.path.join(save_dir, f"{message_id}.ogg")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(file_path, media_type="audio/ogg")

from fastapi import UploadFile, File, Form
from app.services.session_service import SessionService

@router.post("/portal/send/audio")
async def send_audio_from_portal(
    phone_number: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Clinic ID required")
    
    # 1. Set bot_paused to True for this patient
    session = await SessionService.get_session(phone_number, current_user.clinic_id)
    session["bot_paused"] = True
    await SessionService.save_session(phone_number, session, current_user.clinic_id)
    
    # 2. Save the uploaded file locally
    save_dir = os.path.join(os.getcwd(), "uploads", "audio", "outbound")
    os.makedirs(save_dir, exist_ok=True)
    import time
    filename = f"out_{int(time.time())}.ogg"
    file_path = os.path.join(save_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    # 3. Upload to Meta
    ws_srv = WhatsAppService()
    media_id = await ws_srv.upload_media(file_path, mime_type="audio/ogg")
    
    if not media_id:
        raise HTTPException(status_code=500, detail="Failed to upload audio to WhatsApp servers")
        
    # 4. Send the audio message
    res = await ws_srv.send_audio_message(phone_number, media_id)
    
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=str(res.get("error_data")))
        
    # 5. Save to database
    db_msg = await MessageService.save_message(
        db=db,
        clinic_id=current_user.clinic_id,
        sender="Me",
        recipient=phone_number,
        text="[🔊 Sent Audio Note]",
        msg_type="audio",
        whatsapp_message_id=None,
        status="sent"
    )
    
    # Broadcast to websocket
    await manager.broadcast("message_received", {
        "id": f"db_{db_msg.id}",
        "sender": db_msg.sender,
        "recipient": db_msg.recipient,
        "text": db_msg.text,
        "status": db_msg.status,
        "timestamp": db_msg.timestamp.isoformat(),
        "msg_type": "audio"
    })
    
    return {"status": "success"}

class ToggleBotRequest(BaseModel):
    phone_number: str
    bot_paused: bool

@router.post("/portal/session/toggle-bot")
async def toggle_bot(
    req: ToggleBotRequest,
    current_user: User = Depends(get_current_user)
):
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Clinic ID required")
    
    session = await SessionService.get_session(req.phone_number, current_user.clinic_id)
    session["bot_paused"] = req.bot_paused
    await SessionService.save_session(req.phone_number, session, current_user.clinic_id)
    
    return {"status": "success", "bot_paused": req.bot_paused}

@router.get("/portal/session/{phone_number}/status")
async def get_bot_status(
    phone_number: str,
    current_user: User = Depends(get_current_user)
):
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Clinic ID required")
        
    session = await SessionService.get_session(phone_number, current_user.clinic_id)
    return {"status": "success", "bot_paused": session.get("bot_paused", False)}

# --- WebSockets ---

# --- Patient & Messaging Endpoints ---

@router.get("/portal/patients")
async def get_patients(
    search: Optional[str] = None, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Patient)
    if current_user.clinic_id is not None:
        query = query.where(Patient.clinic_id == current_user.clinic_id)
        
    if search:
        search_filter = f"%{search}%"
        query = query.where(or_(
            Patient.name.like(search_filter),
            Patient.phone_number.like(search_filter)
        ))
    result = await db.execute(query.order_by(Patient.name))
    patients = result.scalars().all()
    
    # Enrich patients with their latest message info
    payload = []
    for pat in patients:
        # Normalize phone search for message logs
        clean_phone = pat.phone_number.replace("+", "").strip()
        last_msg_res = await db.execute(
            select(Message)
            .where(or_(
                Message.sender.like(f"%{clean_phone}%"),
                Message.recipient.like(f"%{clean_phone}%")
            ))
            .order_by(Message.timestamp.desc())
            .limit(1)
        )
        last_msg = last_msg_res.scalar_one_or_none()
        payload.append({
            "id": pat.id,
            "name": pat.name,
            "phone_number": pat.phone_number,
            "email": pat.email,
            "created_at": pat.created_at.isoformat(),
            "last_message": {
                "text": last_msg.text if last_msg else None,
                "timestamp": last_msg.timestamp.isoformat() if last_msg else None,
                "status": last_msg.status if last_msg else None
            } if last_msg else None
        })
        
    return payload

@router.delete("/portal/patients/{patient_id}")
async def delete_patient(patient_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Patient).where(Patient.id == patient_id, Patient.clinic_id == current_user.clinic_id)
    res = await db.execute(stmt)
    patient = res.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    await db.delete(patient)
    await db.commit()
    return {"message": "Patient deleted successfully"}

# ----------------- NLP LOGS -----------------

@router.get("/portal/nlp-logs")
async def get_nlp_logs(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(NlpLog).where(NlpLog.clinic_id == current_user.clinic_id).order_by(NlpLog.created_at.desc())
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return logs

@router.put("/portal/nlp-logs/{log_id}/resolve")
async def resolve_nlp_log(log_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(NlpLog).where(NlpLog.id == log_id, NlpLog.clinic_id == current_user.clinic_id)
    res = await db.execute(stmt)
    log = res.scalars().first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    log.reviewed = True
    await db.commit()
    return {"message": "Log marked as resolved"}

@router.get("/portal/patients/{patient_id}/history")
async def get_patient_history(patient_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    clean_phone = patient.phone_number.replace("+", "").strip()
    msg_result = await db.execute(
        select(Message)
        .where(or_(
            Message.sender.like(f"%{clean_phone}%"),
            Message.recipient.like(f"%{clean_phone}%")
        ))
        .order_by(Message.timestamp.asc())
    )
    messages = msg_result.scalars().all()
    
    payload = []
    for msg in messages:
        payload.append({
            "id": msg.whatsapp_message_id or f"db_{msg.id}",
            "sender": msg.sender,
            "recipient": msg.recipient,
            "text": msg.text,
            "status": msg.status,
            "timestamp": msg.timestamp.isoformat(),
            "msg_type": msg.msg_type
        })
    return payload

@router.post("/portal/send")
async def send_portal_message(req: SendMessageRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    number = req.phone_number.strip()
    # Ensure Meta Cloud API expects sender without leading +
    clean_number = number.replace("+", "").strip()
    text = req.text.strip()
    
    if not clean_number or not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number and message text are required"
        )

    # Resolve clinic_id: use user's clinic, or fall back to first clinic for SUPER_ADMIN
    clinic_id = current_user.clinic_id
    if clinic_id is None:
        from app.models.clinic import Clinic
        result = await db.execute(select(Clinic).limit(1))
        first_clinic = result.scalars().first()
        if first_clinic:
            clinic_id = first_clinic.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No clinic found. Please create a clinic first."
            )
        
    whatsapp_service = WhatsAppService()
    res = await whatsapp_service.send_text_message(req.phone_number, req.text)
    
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=str(res.get("error_data")))
        
    # Auto-pause bot when a human sends a text
    from app.services.session_service import SessionService
    session = await SessionService.get_session(req.phone_number, current_user.clinic_id)
    session["bot_paused"] = True
    await SessionService.save_session(req.phone_number, session, current_user.clinic_id)

    # Save to database
    if res.get("status") in ("sent", "logged_locally"):
        api_resp = res.get("api_response", {})
        msg_id = None
        if "messages" in api_resp and len(api_resp["messages"]) > 0:
            msg_id = api_resp["messages"][0].get("id")
            
        # Log to DB
        db_message = await MessageService.save_message(
            db=db,
            sender="Me (You)",
            recipient=clean_number,
            text=text,
            msg_type="text",
            clinic_id=clinic_id,
            whatsapp_message_id=msg_id,
            status="sent"
        )
        
        # Broadcast message event
        msg_payload = {
            "id": db_message.whatsapp_message_id or f"db_{db_message.id}",
            "sender": db_message.sender,
            "recipient": db_message.recipient,
            "text": db_message.text,
            "status": db_message.status,
            "timestamp": db_message.timestamp.isoformat(),
            "msg_type": db_message.msg_type
        }
        await manager.broadcast("message_received", msg_payload)
        
        return {
            "success": True,
            "message": msg_payload
        }
    else:
        error_msg = result.get("error_data", {}).get("error", {}).get("message", "WhatsApp API execution failed")
        return {
            "success": False,
            "error": error_msg
        }

# --- WebSocket Portal Gateway ---

@router.websocket("/portal/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None, db: AsyncSession = Depends(get_db)):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if not payload.get("sub"):
            raise ValueError()
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received text on portal WS: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error on WebSocket connection: {e}")
        manager.disconnect(websocket)
