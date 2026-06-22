from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import logging
from typing import Optional
from sqlalchemy import select, and_
from app.db.session import AsyncSessionLocal
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.timeslot import TimeSlot
from app.models.patient import Patient
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger("scheduler_service")
logger.setLevel(logging.INFO)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None

async def check_no_shows():
    """
    Cron job running every 15 minutes to inspect past slots.
    - If appointment time has passed and status is "scheduled" (never confirmed): mark as "no_show".
    - If appointment time has passed and status is "confirmed": mark as "completed".
    """
    logger.info("Running check_no_shows cron job...")
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.utcnow()
            stmt = (
                select(Appointment, TimeSlot)
                .join(TimeSlot, Appointment.timeslot_id == TimeSlot.id)
                .where(
                    and_(
                        Appointment.status.in_(["scheduled", "confirmed"]),
                        TimeSlot.end_time < now
                    )
                )
            )
            result = await db.execute(stmt)
            rows = result.all()
            
            for appt, slot in rows:
                old_status = appt.status
                if old_status == "scheduled":
                    appt.status = "no_show"
                elif old_status == "confirmed":
                    appt.status = "completed"
                
                logger.info(f"Auto-updating appointment {appt.id} status from {old_status} to {appt.status} (Slot end time: {slot.end_time})")
                
                # Broadcast the status change in real-time
                from app.services.websocket_manager import manager
                await manager.broadcast("appointment_updated", {
                    "id": appt.id,
                    "status": appt.status,
                    "patient_id": appt.patient_id,
                    "doctor_id": appt.doctor_id,
                    "timeslot_id": appt.timeslot_id
                })
                
            if rows:
                await db.commit()
        except Exception as e:
            logger.error(f"Error in check_no_shows job: {e}")

async def send_appointment_reminder(appointment_id: int):
    """
    Job executed by the scheduler.
    Verifies if the appointment is still active and sends a WhatsApp reminder.
    """
    logger.info(f"Triggering reminder job for appointment ID: {appointment_id}...")
    async with AsyncSessionLocal() as db:
        try:
            # Query appointment and load related patient, doctor, timeslot details
            stmt = (
                select(Appointment, Patient, Doctor, TimeSlot)
                .join(Patient, Appointment.patient_id == Patient.id)
                .join(Doctor, Appointment.doctor_id == Doctor.id)
                .join(TimeSlot, Appointment.timeslot_id == TimeSlot.id)
                .where(Appointment.id == appointment_id)
            )
            result = await db.execute(stmt)
            row = result.first()
            if not row:
                logger.warning(f"Reminder Job failed: Appointment {appointment_id} not found in DB.")
                return
                
            appt, patient, doctor, slot = row
            
            # Send reminder only if it is still scheduled
            if appt.status != "scheduled":
                logger.info(f"Reminder skipped: Appointment {appointment_id} status is '{appt.status}'.")
                return
                
            logger.info(f"Sending reminder to Patient {patient.name} ({patient.phone_number})...")
            
            # Format timeslot presentation
            start_str = slot.start_time.strftime("%I:%M %p on %B %d, %Y")
            reminder_text = (
                f"Reminder: You have an upcoming appointment with {doctor.name} ({doctor.specialty}) "
                f"scheduled at {start_str}.\n\n"
                f"Please confirm or reschedule your booking below."
            )
            
            # Buttons payload
            buttons = [
                {"id": f"btn_rem_confirm_{appt.id}", "title": "Confirm Booking"},
                {"id": f"btn_rem_resch_{appt.id}", "title": "Reschedule"}
            ]
            
            whatsapp_service = WhatsAppService()
            await whatsapp_service.send_interactive_buttons(
                recipient_id=patient.phone_number,
                text=reminder_text,
                buttons=buttons
            )
            logger.info(f"Reminder message successfully dispatched to {patient.phone_number}.")
        except Exception as e:
            logger.error(f"Error in send_appointment_reminder for appointment {appointment_id}: {e}")

class SchedulerService:
    @classmethod
    def start(cls) -> None:
        global _scheduler
        if _scheduler is None:
            _scheduler = AsyncIOScheduler()
            _scheduler.start()
            logger.info("AsyncIOScheduler started successfully.")
            
            # Schedule check_no_shows cron job to run every 15 minutes
            _scheduler.add_job(
                check_no_shows,
                "interval",
                minutes=15,
                id="check_no_shows_job"
            )
            logger.info("Scheduled check_no_shows job to run every 15 minutes.")

    @classmethod
    def shutdown(cls) -> None:
        global _scheduler
        if _scheduler is not None:
            _scheduler.shutdown()
            _scheduler = None
            logger.info("AsyncIOScheduler shut down successfully.")

    @classmethod
    def schedule_reminder(cls, appointment_id: int, run_time: datetime) -> None:
        global _scheduler
        if _scheduler is None:
            cls.start()
            
        # If run_time is in the past, schedule it for 5 seconds in the future for demonstration purposes
        now = datetime.utcnow()
        if run_time <= now:
            logger.warning(f"Reminder run_time {run_time} is in the past. Scheduling 5 seconds in the future for demo.")
            run_time = now + timedelta(seconds=5)
            
        job_id = f"appt_reminder_{appointment_id}"
        
        # Remove existing job if present
        try:
            if _scheduler.get_job(job_id):
                _scheduler.remove_job(job_id)
        except Exception:
            pass
            
        _scheduler.add_job(
            send_appointment_reminder,
            "date",
            run_date=run_time,
            args=[appointment_id],
            id=job_id
        )
        logger.info(f"Scheduled reminder job '{job_id}' to run at {run_time}.")
