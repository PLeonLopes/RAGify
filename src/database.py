import sqlite3
import os
from datetime import datetime

DB_NAME = "sqlite3.db"                          # Sqlite3 DB
FAISS_BASE_PATH = "faiss_user_index"            # FAISS indexes

if not os.path.exists(FAISS_BASE_PATH):
    os.makedirs(FAISS_BASE_PATH)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # "users" table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)
    
    # "chat_history" table (Stores user question and LLM answer pairs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_message TEXT,
        ai_response TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # "user_files" table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        faiss_index_subpath TEXT, -- Subcaminho específico do índice do usuário
        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    conn.commit()
    conn.close()

def add_user(username, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        user_faiss_path = os.path.join(FAISS_BASE_PATH, str(user_id))           # Creates FAISS index by ID
        if not os.path.exists(user_faiss_path):
            os.makedirs(user_faiss_path)
        return user_id
    except sqlite3.IntegrityError:          # User already exists
        return None
    finally:
        conn.close()

def get_user(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()            # Object or "None"
    conn.close()
    return user

# Chat History
def save_chat_message(user_id, user_message, ai_response):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_id, user_message, ai_response) VALUES (?, ?, ?)",
                   (user_id, user_message, ai_response))
    conn.commit()
    conn.close()

def load_chat_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_message, ai_response FROM chat_history WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
    history_tuples = cursor.fetchall()          # tuple -> (AI_MESSAGE, USER_MESSAGE)
    conn.close()
    return history_tuples

def add_user_file_record(user_id, filename, faiss_index_subpath):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Prevents file name duplication
    cursor.execute("SELECT id FROM user_files WHERE user_id = ? AND filename = ? AND faiss_index_subpath = ?", 
                   (user_id, filename, faiss_index_subpath))
    existing = cursor.fetchone()
    if not existing:
        cursor.execute("INSERT INTO user_files (user_id, filename, faiss_index_subpath) VALUES (?, ?, ?)",
                       (user_id, filename, faiss_index_subpath))
        conn.commit()
    conn.close()

def get_user_files(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, faiss_index_subpath, processed_at FROM user_files WHERE user_id = ? ORDER BY processed_at DESC", (user_id,))
    files = cursor.fetchall()
    conn.close()
    return files

def delete_user_file(file_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_files WHERE id = ?", (file_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0

# Returns FAISS index path (Auxiliary Function)
def get_user_faiss_path(user_id):
    return os.path.join(FAISS_BASE_PATH, str(user_id))

# Creates tables on the first import, if necessary
create_tables()