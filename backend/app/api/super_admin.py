from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.clinic import Clinic
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.api.deps import require_super_admin

router = APIRouter()

class ClinicCreate(BaseModel):
    name: str
    wa_phone_number_id: str
    timezone: str = "UTC"

class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    clinic_id: int

@router.post("/clinics", response_model=dict)
async def create_clinic(
    clinic_in: ClinicCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_super_admin)
):
    """
    Creates a new Clinic tenant. Accessible only to Super Admins.
    """
    stmt = select(Clinic).where(Clinic.wa_phone_number_id == clinic_in.wa_phone_number_id)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Clinic with this WhatsApp Phone ID already exists.")
        
    clinic = Clinic(
        name=clinic_in.name,
        wa_phone_number_id=clinic_in.wa_phone_number_id,
        timezone=clinic_in.timezone
    )
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)
    return {"id": clinic.id, "name": clinic.name, "wa_phone_number_id": clinic.wa_phone_number_id}

@router.post("/users", response_model=dict)
async def create_clinic_admin(
    user_in: AdminCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_super_admin)
):
    """
    Creates a new Clinic Admin user. Accessible only to Super Admins.
    """
    stmt = select(User).where(User.email == user_in.email)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists.")
        
    # Check clinic exists
    clinic_stmt = select(Clinic).where(Clinic.id == user_in.clinic_id)
    c_res = await db.execute(clinic_stmt)
    if not c_res.scalars().first():
        raise HTTPException(status_code=404, detail="Clinic not found.")
        
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=UserRole.CLINIC_ADMIN,
        clinic_id=user_in.clinic_id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role.value, "clinic_id": user.clinic_id}
