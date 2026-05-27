import os
import sqlite3
from datetime import datetime

DATABASE_NAME = "posts_log.db"

def get_db_connection():
    """Establishes connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            topic TEXT NOT NULL,
            template_type TEXT NOT NULL,
            headline TEXT NOT NULL,
            image_path TEXT,
            video_path TEXT,
            metadata_path TEXT,
            vision_rating INTEGER,
            vision_feedback TEXT,
            caption_ig TEXT,
            caption_tiktok TEXT,
            caption_shorts TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"DATABASE: SQLite database '{DATABASE_NAME}' initialized.")

def log_generation(topic, template_type, headline, image_path, video_path, metadata_path, vision_rating, vision_feedback, captions):
    """Logs a single generation run into the database."""
    init_db()  # Make sure tables exist
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO generation_logs (
            timestamp, topic, template_type, headline, image_path, video_path, metadata_path, 
            vision_rating, vision_feedback, caption_ig, caption_tiktok, caption_shorts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        topic,
        template_type,
        headline,
        image_path,
        video_path,
        metadata_path,
        vision_rating,
        vision_feedback,
        captions.get("instagram", ""),
        captions.get("tiktok", ""),
        captions.get("shorts", "")
    ))
    
    conn.commit()
    conn.close()
    print("DATABASE: Generation successfully logged to SQLite database.")

def get_recent_logs(limit=10):
    """Retrieves recent logs."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generation_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    init_db()
