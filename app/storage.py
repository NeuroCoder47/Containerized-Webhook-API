import sqlite3
from app.config import DATABASE_URL
from datetime import datetime

def get_connection():
    db_path = DATABASE_URL.replace("sqlite:///", "")
    connection_obj = sqlite3.connect(db_path)
    return connection_obj

def message_exists( m_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM messages WHERE message_id = ?",(m_id,))
    result = cursor.fetchone()
    connection.close()
    return result is not None

def insert_message(message_id, from_msisdn, to_msisdn, ts, text ):
    connection = get_connection()
    created_at = datetime.utcnow().isoformat() + "Z"
    cursor = connection.cursor()
    cursor.execute("INSERT INTO messages(  message_id,from_msisdn,to_msisdn,ts,text,created_at) VALUES (?, ?, ?, ?, ?, ?)",(message_id, from_msisdn, to_msisdn, ts, text, created_at))
    connection.commit()
    connection.close()

def get_messages(limit=50, offset=0, from_=None, since=None, q=None):
    connection = get_connection()
    cursor = connection.cursor()

    conditions = []
    params = []

    if from_:
        conditions.append("from_msisdn = ?")
        params.append(from_)

    if since:
        conditions.append("ts >= ?")
        params.append(since)

    if q:
        conditions.append("text LIKE ?")
        params.append(f"%{q}%")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    count_query = f"SELECT COUNT(*) FROM messages {where_clause}"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    data_query = f"SELECT * FROM messages {where_clause} ORDER BY ts ASC, message_id ASC LIMIT ? OFFSET ?"
    cursor.execute(data_query, params + [limit, offset])
    rows = cursor.fetchall()

    messages = []
    for row in rows:
        messages.append({
            "message_id": row[0],
            "from": row[1],
            "to": row[2],
            "ts": row[3],
            "text": row[4],
            "created_at": row[5]
        })

    connection.close()
    return messages, total


def get_stats():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT from_msisdn) FROM messages")
    senders_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT from_msisdn, COUNT(*) as count 
        FROM messages 
        GROUP BY from_msisdn 
        ORDER BY count DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    messages_per_sender = [{"from": row[0], "count": row[1]} for row in rows]

    cursor.execute("SELECT MIN(ts), MAX(ts) FROM messages")
    row = cursor.fetchone()
    first_message_ts = row[0]
    last_message_ts = row[1]

    connection.close()

    return {
        "total_messages": total_messages,
        "senders_count": senders_count,
        "messages_per_sender": messages_per_sender,
        "first_message_ts": first_message_ts,
        "last_message_ts": last_message_ts
    }

