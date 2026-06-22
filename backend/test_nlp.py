import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.services.booking_flow import BookingFlow
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    async with SessionLocal() as db:
        try:
            print("Running BookingFlow.handle_message...")
            await BookingFlow.handle_message(
                phone_number="15550000000",
                sender_name="Test User",
                msg_type="text",
                text_or_payload="Hi, I need an appointment",
                db=db,
                clinic_id=1
            )
            print("Done!")
        except Exception as e:
            logging.exception("Error occurred:")

asyncio.run(main())
