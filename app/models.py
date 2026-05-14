import sqlite3
from app.config import DATABASE_URL

def init_db():
    db_path = DATABASE_URL.replace("sqlite:///", "")
    connection_obj = sqlite3.connect(db_path)
    cursor_obj = connection_obj.cursor()
    cursor_obj.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        message_id  TEXT PRIMARY KEY,
        from_msisdn TEXT NOT NULL,
        to_msisdn   TEXT NOT NULL,
        ts          TEXT NOT NULL,
        text        TEXT,
        created_at  TEXT NOT NULL)
    """)
    connection_obj.commit()
    connection_obj.close()
    print("Database initialised successfully.")