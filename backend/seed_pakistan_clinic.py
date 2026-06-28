import sqlite3
import os

def seed():
    db_path = os.path.join(os.path.dirname(__file__), "chatbot.db")
    if not os.path.exists(db_path):
        print("DB not found at", db_path)
        return
            
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Update Clinic Data with Pakistani Context
    address = "14-B, Block 6, PECHS, Shahrah-e-Faisal, Karachi, Pakistan"
    working_hours = "Monday to Saturday: 10:00 AM to 10:00 PM. Sunday: Closed."
    general_info = (
        "Welcome to Al-Shifa Health Clinic. "
        "Services offered: General Physician Consultation, Blood Tests, X-Rays, Ultrasound, and Dental Surgery. "
        "Consultation fee ranges from Rs. 1000 to Rs. 2500. "
        "We accept Sehat Sahulat Card and major health insurances."
    )
    
    try:
        # Assuming there is at least 1 clinic, update the first one
        cursor.execute('''
            UPDATE clinics 
            SET address = ?, working_hours = ?, general_info = ?
            WHERE id = (SELECT id FROM clinics LIMIT 1)
        ''', (address, working_hours, general_info))
        print("Updated Clinic data with Pakistani context.")
    except Exception as e:
        print("Error updating clinic:", e)

    # 2. Update existing doctors with bios or insert if none exist
    try:
        # Check if doctors exist
        cursor.execute("SELECT id, name FROM doctors")
        doctors = cursor.fetchall()
        
        if doctors:
            for doc in doctors:
                doc_id, doc_name = doc
                bio = f"{doc_name} is a highly experienced specialist practicing in Karachi. They have over 10 years of experience in treating complex cases and are known for their patient-friendly approach."
                cursor.execute('UPDATE doctors SET bio = ? WHERE id = ?', (bio, doc_id))
            print("Updated existing doctors with sample bios.")
        else:
            # Insert a sample doctor if none exist
            cursor.execute('''
                INSERT INTO doctors (clinic_id, name, specialty, phone_number, email, bio, created_at)
                VALUES (1, 'Dr. Ahmed Raza', 'General Physician', '+923001234567', 'ahmed@alshifa.pk', 
                'Dr. Ahmed Raza has 15 years of experience in internal medicine at Jinnah Hospital. He specializes in diabetes management and seasonal fevers.',
                CURRENT_TIMESTAMP)
            ''')
            print("Inserted a sample Pakistani doctor.")
            
    except Exception as e:
        print("Error updating doctors:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed()
