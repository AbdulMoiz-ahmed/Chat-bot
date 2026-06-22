import asyncio
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, engine
from app.models.doctor import Doctor
from app.models.timeslot import TimeSlot
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.services.session_service import SessionService
from app.services.booking_flow import BookingFlow

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("verify_booking_flow")

async def test_booking_flow():
    logger.info("Starting automated WhatsApp Booking Flow simulator...")
    phone = "923999999999"
    name = "Test Simulator User"

    async with AsyncSessionLocal() as db:
        # Clear previous state
        await SessionService.clear_session(phone)
        
        # 1. Fetch available doctor and timeslots
        logger.info("\n=== Step 1: Simulating 'book' keyword ===")
        doc_res = await db.execute(select(Doctor))
        doctor = doc_res.scalars().first()
        if not doctor:
            logger.error("No doctors found in DB. Run init_db.py first!")
            return
            
        logger.info(f"Targeting Doctor: Dr. {doctor.name} (ID: {doctor.id})")
        
        # Simulate typing 'book'
        await BookingFlow.handle_message(
            phone_number=phone,
            sender_name=name,
            msg_type="text",
            text_or_payload="book",
            db=db
        )
        
        # Verify state transition
        sess = await SessionService.get_session(phone)
        logger.info(f"Session state after 'book': {sess}")
        assert sess["step"] == "select_doctor", "Step did not transition to select_doctor!"
        
        # 2. Simulate selecting the doctor
        logger.info("\n=== Step 2: Simulating Doctor Selection (list reply) ===")
        await BookingFlow.handle_message(
            phone_number=phone,
            sender_name=name,
            msg_type="interactive",
            text_or_payload=f"doc_{doctor.id}",
            db=db
        )
        
        # Verify state transition
        sess = await SessionService.get_session(phone)
        logger.info(f"Session state after doctor selection: {sess}")
        assert sess["step"] == "select_date", "Step did not transition to select_date!"
        
        # 3. Simulate selecting the date
        logger.info("\n=== Step 3: Simulating Date Selection (list reply) ===")
        # Get a timeslot for this doctor
        slot_res = await db.execute(select(TimeSlot).where(TimeSlot.doctor_id == doctor.id, TimeSlot.is_available == True))
        slot = slot_res.scalars().first()
        if not slot:
            logger.error("No available timeslots found for this doctor in DB.")
            return
            
        date_str = slot.start_time.date().isoformat()
        await BookingFlow.handle_message(
            phone_number=phone,
            sender_name=name,
            msg_type="interactive",
            text_or_payload=f"date_{date_str}",
            db=db
        )
        
        # Verify state transition
        sess = await SessionService.get_session(phone)
        logger.info(f"Session state after date selection: {sess}")
        assert sess["step"] == "select_slot", "Step did not transition to select_slot!"
        
        # 4. Simulate selecting the slot
        logger.info("\n=== Step 4: Simulating Slot Selection (list reply) ===")
        await BookingFlow.handle_message(
            phone_number=phone,
            sender_name=name,
            msg_type="interactive",
            text_or_payload=f"slot_{slot.id}",
            db=db
        )
        
        # Verify state transition
        sess = await SessionService.get_session(phone)
        logger.info(f"Session state after slot selection: {sess}")
        assert sess["step"] == "confirm", "Step did not transition to confirm!"
        
        # 5. Simulate booking confirmation
        logger.info("\n=== Step 5: Simulating Booking Confirmation (button reply) ===")
        await BookingFlow.handle_message(
            phone_number=phone,
            sender_name=name,
            msg_type="interactive",
            text_or_payload="btn_confirm",
            db=db
        )
        
        # Verify final state is cleared
        sess = await SessionService.get_session(phone)
        logger.info(f"Session state after confirmation: {sess}")
        assert sess["step"] == "idle", "Step did not clear to idle!"
        
        # Verify database changes
        logger.info("\n=== Step 6: Verifying database entries ===")
        # Check timeslot status
        slot_stmt = select(TimeSlot).where(TimeSlot.id == slot.id)
        slot_updated = (await db.execute(slot_stmt)).scalars().first()
        logger.info(f"Timeslot ID {slot.id} availability: {slot_updated.is_available}")
        assert slot_updated.is_available is False, "Timeslot was not marked unavailable in database!"
        
        # Check appointment created
        appt_stmt = select(Appointment).where(Appointment.timeslot_id == slot.id, Appointment.status == "scheduled")
        appt = (await db.execute(appt_stmt)).scalars().first()
        assert appt is not None, "Appointment was not created in database!"
        logger.info(f"Appointment successfully created: ID {appt.id}, Patient ID {appt.patient_id}, Doctor ID {appt.doctor_id}")
        
        # Clean up created appointment and restore timeslot for next tests
        logger.info("\n=== Step 7: Cleaning up test records ===")
        await db.delete(appt)
        slot_updated.is_available = True
        await db.commit()
        logger.info("Test records successfully cleaned up!")
        logger.info("\n🎉 All booking flow simulations and database assertions passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_booking_flow())
