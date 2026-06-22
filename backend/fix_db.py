import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings

async def main():
    print(f"Connecting to {settings.DATABASE_URL}...")
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    async with SessionLocal() as db:
        await db.execute(text("UPDATE clinics SET wa_phone_number_id='1181649411696421' WHERE id=1"))
        await db.commit()
        print("Updated Clinic 1 to use wa_phone_number_id '1181649411696421'")

asyncio.run(main())
