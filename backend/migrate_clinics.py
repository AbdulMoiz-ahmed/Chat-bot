import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "chatbot.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), "database.db")
        if not os.path.exists(db_path):
            print("DB not found")
            return
            
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE clinics ADD COLUMN address VARCHAR")
        print("Added address to clinics")
    except Exception as e:
        print("address error:", e)

    try:
        cursor.execute("ALTER TABLE clinics ADD COLUMN working_hours VARCHAR")
        print("Added working_hours to clinics")
    except Exception as e:
        print("working_hours error:", e)

    try:
        cursor.execute("ALTER TABLE clinics ADD COLUMN general_info VARCHAR")
        print("Added general_info to clinics")
    except Exception as e:
        print("general_info error:", e)

    try:
        cursor.execute("ALTER TABLE doctors ADD COLUMN bio VARCHAR")
        print("Added bio to doctors")
    except Exception as e:
        print("bio error:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
