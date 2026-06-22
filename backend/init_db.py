import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select

from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.timeslot import TimeSlot
from app.models.appointment import Appointment
from app.models.message import Message
from app.models.user import User, UserRole
from app.core.security import get_password_hash

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("init_db")

async def init_db():
    logger.info("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        # Create all tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables checked/created successfully.")

    # Seed some initial data for demonstration purposes
    async with AsyncSessionLocal() as db:
        # Check if we already have doctors
        result = await db.execute(select(Doctor))
        if result.scalars().first():
            logger.info("Database already contains data, skipping seeding.")
            return

        logger.info("Seeding database with default records...")
        
        # 0. Add Clinic
        clinic = Clinic(
            name="Test Clinic",
            wa_phone_number_id="1234567890", # Replace with actual or test number ID
            timezone="UTC"
        )
        db.add(clinic)
        await db.commit()
        await db.refresh(clinic)
        logger.info(f"Added clinic: {clinic.name} (ID: {clinic.id})")

        # 0.5 Add Users (Super Admin and Clinic Admin)
        super_admin = User(
            email="super_admin@example.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.SUPER_ADMIN,
            clinic_id=None
        )
        clinic_admin = User(
            email="clinic_admin@example.com",
            password_hash=get_password_hash("clinic123"),
            role=UserRole.CLINIC_ADMIN,
            clinic_id=clinic.id
        )
        db.add_all([super_admin, clinic_admin])
        await db.commit()
        logger.info("Added default users: super_admin@example.com and clinic_admin@example.com")

        # 1. Add Doctors
        doc1 = Doctor(
            clinic_id=clinic.id,
            name="Dr. Sarah Jenkins", 
            specialty="Cardiology", 
            email="sarah.jenkins@example.com", 
            phone_number="+15550101"
        )
        doc2 = Doctor(
            clinic_id=clinic.id,
            name="Dr. Robert Chen", 
            specialty="Pediatrics", 
            email="robert.chen@example.com", 
            phone_number="+15550102"
        )
        db.add_all([doc1, doc2])
        await db.commit()
        await db.refresh(doc1)
        await db.refresh(doc2)
        logger.info(f"Added doctors: {doc1.name} (ID: {doc1.id}), {doc2.name} (ID: {doc2.id})")

        # 2. Add Patients
        pat1 = Patient(
            clinic_id=clinic.id,
            name="John Doe", 
            phone_number="+1234567890", 
            email="john.doe@example.com"
        )
        pat2 = Patient(
            clinic_id=clinic.id,
            name="Jane Smith", 
            phone_number="+1987654321", 
            email="jane.smith@example.com"
        )
        db.add_all([pat1, pat2])
        await db.commit()
        await db.refresh(pat1)
        await db.refresh(pat2)
        logger.info(f"Added patients: {pat1.name} (ID: {pat1.id}), {pat2.name} (ID: {pat2.id})")

        # 3. Add TimeSlots (availability slots for doctors)
        # We define slots starting from tomorrow
        tomorrow = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        slot1 = TimeSlot(
            clinic_id=clinic.id,
            doctor_id=doc1.id,
            start_time=tomorrow,
            end_time=tomorrow + timedelta(minutes=30),
            is_available=True
        )
        slot2 = TimeSlot(
            clinic_id=clinic.id,
            doctor_id=doc1.id,
            start_time=tomorrow + timedelta(minutes=30),
            end_time=tomorrow + timedelta(hours=1),
            is_available=False  # Booked slot
        )
        slot3 = TimeSlot(
            clinic_id=clinic.id,
            doctor_id=doc2.id,
            start_time=tomorrow + timedelta(hours=2),
            end_time=tomorrow + timedelta(hours=2, minutes=30),
            is_available=True
        )
        db.add_all([slot1, slot2, slot3])
        await db.commit()
        await db.refresh(slot1)
        await db.refresh(slot2)
        await db.refresh(slot3)
        logger.info("Added timeslots.")

        # 4. Add an Appointment corresponding to the booked slot (slot2)
        app1 = Appointment(
            clinic_id=clinic.id,
            patient_id=pat1.id,
            doctor_id=doc1.id,
            timeslot_id=slot2.id,
            status="scheduled"
        )
        db.add(app1)
        await db.commit()
        await db.refresh(app1)
        logger.info(f"Created appointment: Patient {pat1.name} with {doc1.name} at {slot2.start_time} (ID: {app1.id})")
        
        logger.info("Database seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
